import sys
import os
import subprocess
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import toml
import json
import glob
import asyncio
try:
    from .platform_support import accelerator_info, schedule_shutdown, training_hardware_error
except ImportError:  # Direct execution: python backend/main.py
    from platform_support import accelerator_info, schedule_shutdown, training_hardware_error

app = FastAPI()


def get_accelerator_training_error():
    try:
        import torch
    except Exception as e:
        launcher = "start.bat" if os.name == "nt" else "./start.sh"
        return f"PyTorchの読み込みに失敗しました。{launcher}を再実行してください。 / Failed to load PyTorch: {e}"
    return training_hardware_error(torch)


def open_native_dialog(kind: str, title: str) -> str:
    """Open a desktop picker lazily so headless Linux servers can still start."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError(
            "Folder picker is unavailable. Install python3-tk or enter the path manually."
        ) from exc

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if kind == "folder":
            return filedialog.askdirectory(parent=root, title=title)
        return filedialog.askopenfilename(
            parent=root,
            title=title,
            filetypes=[("Safetensors", "*.safetensors"), ("All Files", "*.*")],
        )
    except tk.TclError as exc:
        raise RuntimeError(
            "Desktop picker is unavailable (no graphical display). Enter the path manually."
        ) from exc
    finally:
        if "root" in locals():
            root.destroy()

# Supported image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HISTORY_PATH = os.path.join(DATA_DIR, "training_history.json")
HISTORY_LIMIT = 30

def count_dataset_images(path):
    if not path or not os.path.exists(path):
        return 0
    return sum(
        1
        for f in os.listdir(path)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
    )

def load_training_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def collect_trigger_words(path):
    if not path or not os.path.exists(path):
        return []

    trigger_words = []
    seen = set()
    for txt_path in glob.glob(os.path.join(path, "*.txt")):
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                tags = [tag.strip() for tag in f.read().split(",") if tag.strip()]
        except Exception:
            continue

        for tag in tags:
            if tag.startswith("@") and tag not in seen:
                trigger_words.append(tag)
                seen.add(tag)

    return trigger_words[:10]
def save_training_history(config):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        image_count = count_dataset_images(config.path)
        repeats = max(config.repeats, 1)
        epochs = max(config.epochs, 0)
        entry = {
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "dataset_path": config.path,
            "output_dir": config.output_dir,
            "name": config.name,
            "image_count": image_count,
            "estimated_steps": image_count * repeats * epochs,
            "trigger_words": collect_trigger_words(config.path),
            "settings": {
                "epochs": config.epochs,
                "repeats": config.repeats,
                "lr": config.lr,
                "rank": config.rank,
                "alpha": config.alpha,
                "vram": config.vram,
                "optimizer_type": config.optimizer_type,
                "optimizer_args": config.optimizer_args,
                "optimizer_low_vram": config.optimizer_low_vram,
                "dataloader_workers": config.dataloader_workers,
                "flip_aug": config.flip_aug,
                "shuffle_caption": config.shuffle_caption,
                "keep_tokens": config.keep_tokens,
                "min_snr_gamma": config.min_snr_gamma,
                "min_snr_gamma_value": config.min_snr_gamma_value,
                "keep_unet": getattr(config, "keep_unet", False),
                "shutdown": config.shutdown
            }
        }
        history = [entry] + load_training_history()
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history[:HISTORY_LIMIT], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save training history: {e}")

@app.get("/api/training-history")
async def get_training_history():
    return {"history": load_training_history()}

def get_tag_category(tag):
    tag = tag.strip().lower()
    if tag.startswith("@") or tag in ["1girl", "1boy", "girl", "boy", "solo"]:
        return "tag-char"
    if any(x in tag for x in ["hair", "eyes", "skin", "body"]):
        return "tag-char"
    if any(x in tag for x in ["shirt", "skirt", "pants", "dress", "uniform", "clothes", "wearing"]):
        return "tag-clothes"
    if any(x in tag for x in ["background", "outdoor", "indoor", "room", "sky", "tree", "nature"]):
        return "tag-bg"
    if any(x in tag for x in ["masterpiece", "best quality", "highres", "year", "score"]):
        return "tag-meta"
    return "tag-general"

def generate_dataset_toml(image_dir, output_path, repeats=2):
    config = {
        "general": {
            "enable_bucket": True,
            "resolution": [1024, 1024],
            "min_bucket_reso": 256,
            "max_bucket_reso": 2048,
            "caption_extension": ".txt"
        },
        "datasets": [
            {
                "subsets": [
                    {
                        "image_dir": image_dir,
                        "num_repeats": repeats
                    }
                ]
            }
        ]
    }
    with open(output_path, "w") as f:
        toml.dump(config, f)

# Global variable to store logs and active connections
training_logs = ""
tagging_logs = "" # Separate logs for tagging
training_process = None
setup_running = False
setup_succeeded = None
active_connections: list[WebSocket] = []

def build_sd_scripts_env(script_path: str) -> dict:
    env = os.environ.copy()
    env.pop("ACCELERATE_USE_CPU", None)
    existing_pythonpath = env.get("PYTHONPATH", "")
    paths = [script_path]
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send a combined current state or just wait for broadcasts
        await websocket.send_text("--- Connection Established ---")
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_log(line: str, type="train"):
    global training_logs, tagging_logs
    prefix = "[TRAIN] " if type == "train" else "[TAGGER] "
    full_line = prefix + line
    
    if type == "train":
        training_logs += full_line
    else:
        tagging_logs += full_line
    
    for connection in active_connections:
        try:
            await connection.send_text(full_line)
        except:
            pass

class TrainingConfig(BaseModel):
    path: str
    model: str
    vae: str = ""
    qwen3: str = ""
    output_dir: str
    name: str
    vram: str
    epochs: int
    repeats: int = 2
    lr: str
    rank: int = 4
    alpha: int = 1
    flip_aug: bool = False
    shuffle_caption: bool = False
    keep_tokens: int = 1
    min_snr_gamma: bool = False
    min_snr_gamma_value: float = 5.0
    keep_unet: bool = False
    shutdown: bool = False
    optimizer_type: str = "AdamW"
    optimizer_args: str = ""
    optimizer_low_vram: bool = False
    dataloader_workers: int = 0

@app.post("/api/start-training")
async def start_training(config: TrainingConfig, script_path: str = ""):
    global training_logs, training_process
    
    if training_process and training_process.poll() is None:
        return {"status": "error", "message": "Training is already running"}

    accelerator_error = get_accelerator_training_error()
    if accelerator_error:
        return {"status": "error", "message": accelerator_error}

    training_logs = "Initializing training...\n"
    
    # Check script path
    internal_scripts = os.path.join(os.path.dirname(__file__), "sd-scripts")
    train_script_name = "anima_train_network.py"
    
    if not script_path and os.path.exists(internal_scripts):
        script_path = internal_scripts
        
    train_script = os.path.join(script_path, train_script_name) if script_path else train_script_name
    
    if not os.path.exists(train_script):
        msg = f"Error: {train_script} が見つかりません。sd-scriptsのパスを確認するか、セットアップを行ってください。\n"
        await broadcast_log(msg, "train")
        return {"status": "error", "message": "Script not found"}

    # Validate required Anima parameters
    if not config.model:
        return {"status": "error", "message": "ベースモデルのパス(Base Model Path)が指定されていません。"}
    if not config.vae:
        return {"status": "error", "message": "VAEのパスが指定されていません。Animaの学習には専用のVAEが必要です。"}
    if not config.qwen3:
        return {"status": "error", "message": "Qwen3テキストエンコーダーのパスが指定されていません。Animaの学習にはQwen3が必要です。"}

    # Generate dataset TOML
    toml_path = os.path.join(os.getcwd(), "dataset_config.toml")
    try:
        generate_dataset_toml(config.path, toml_path, max(config.repeats, 1))
        training_logs += f"Generated dataset config at {toml_path}\n"
        save_training_history(config)
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate TOML: {str(e)}"}

    # In a real scenario, we would run sd-scripts
    command = [
        sys.executable, train_script,
        f"--pretrained_model_name_or_path={config.model}",
        f"--output_dir={config.output_dir}",
        f"--output_name={config.name}",
        f"--dataset_config={toml_path}",
        "--network_module=networks.lora_anima",
        f"--max_train_epochs={config.epochs}",
        f"--learning_rate={config.lr}",
        f"--network_dim={config.rank}",
        f"--network_alpha={config.alpha}",
        "--mixed_precision=bf16",
        "--gradient_checkpointing",
        f"--max_data_loader_n_workers={max(config.dataloader_workers, 0)}"
    ]
    
    if config.vae:
        command.append(f"--vae={config.vae}")
    if config.qwen3:
        command.append(f"--qwen3={config.qwen3}")
    if config.flip_aug:
        command.append("--flip_aug")
    if config.shuffle_caption:
        command.append("--shuffle_caption")
        command.append(f"--keep_tokens={max(config.keep_tokens, 0)}")
    if config.min_snr_gamma:
        command.append(f"--min_snr_gamma={config.min_snr_gamma_value}")

    # Optimizer selection (defaults to AdamW when left blank/unset, matching sd-scripts default)
    use_custom_optimizer = bool(config.optimizer_type) and config.optimizer_type.lower() != "adamw"
    if use_custom_optimizer:
        command.append(f"--optimizer_type={config.optimizer_type}")
        if config.optimizer_args.strip():
            command.append("--optimizer_args")
            command.extend(config.optimizer_args.strip().split())

    # Add VRAM optimizations
    blocks_to_swap = 0
    if config.vram == "low":
        blocks_to_swap = 20
    elif config.vram == "balanced":
        blocks_to_swap = 10

    if use_custom_optimizer and config.optimizer_low_vram:
        # Prodigy/DAdaptation keep extra per-parameter state, so swap a few more blocks to offset it
        blocks_to_swap += 6

    if blocks_to_swap > 0:
        command.append(f"--blocks_to_swap={blocks_to_swap}")

    # Update output name to include _unet suffix
    for i, arg in enumerate(command):
        if arg.startswith("--output_name="):
            command[i] = f"--output_name={config.name}_unet"

    training_logs = f"Running command: {' '.join(command)}\n"
    
    try:
        # Run process and conversion in a task
        asyncio.create_task(train_and_convert_task(config, command, script_path))
        return {"status": "started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def train_and_convert_task(config: TrainingConfig, command: list, script_path: str):
    global training_process
    try:
        # 1. Run Training
        training_process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            encoding="utf-8",
            errors="replace",
            env=build_sd_scripts_env(script_path)
        )
        await run_and_capture(training_process, "train")
        
        if training_process.returncode != 0:
            await broadcast_log("Training failed. Skipping conversion.\n", "train")
            return

        # 2. Run Conversion
        await broadcast_log("\n--- Starting Conversion to ComfyUI ---\n", "train")
        
        src_path = os.path.join(config.output_dir, f"{config.name}_unet.safetensors")
        dst_path = os.path.join(config.output_dir, f"{config.name}_comfy.safetensors")
        
        convert_script = os.path.join(script_path, "networks", "convert_anima_lora_to_comfy.py")
        if not os.path.exists(convert_script):
             await broadcast_log(f"Error: Conversion script not found at {convert_script}\n", "train")
             return

        conv_command = [sys.executable, convert_script, src_path, dst_path]
        
        conv_process = subprocess.Popen(
            conv_command,
            cwd=script_path,
            env=build_sd_scripts_env(script_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        await run_and_capture(conv_process, "train")

        if conv_process.returncode != 0:
            await broadcast_log("Conversion failed. Keeping temporary UNET file.\n", "train")
            return
        
        # 3. Cleanup
        if not config.keep_unet:
            await broadcast_log(f"Cleaning up temporary UNET file: {os.path.basename(src_path)}\n", "train")
            if os.path.exists(src_path):
                os.remove(src_path)
        
        await broadcast_log("\n--- All Processes Finished Successfully ---\n", "train")
        
        if config.shutdown:
            await broadcast_log("\n⚠️ シャットダウン命令を受信しました。60秒後にPCをシャットダウンします。\n", "train")
            scheduled, detail = schedule_shutdown()
            if scheduled:
                await broadcast_log(f"中止コマンド / Cancel command: {detail}\n", "train")
            else:
                await broadcast_log(f"自動シャットダウンの予約に失敗しました: {detail}\n", "train")
        
    except Exception as e:
        await broadcast_log(f"Critical Error in process chain: {str(e)}\n", "train")

async def run_and_capture(process, type):
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, process.stdout.readline)
        if not line:
            break
        
        # Filter out noisy but harmless warnings
        if "triton not found" in line or "not compatible with the current PyTorch installation" in line:
            continue
            
        await broadcast_log(line, type)
    process.wait()
    await broadcast_log(f"\n--- {type.upper()} Finished ---\n", type)

@app.get("/api/browse-folder")
async def browse_folder():
    try:
        folder_path = open_native_dialog("folder", "Select Folder")
        if folder_path:
            return {"path": folder_path}
        return {"path": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/browse-file")
async def browse_file():
    try:
        file_path = open_native_dialog("file", "Select Model")
        if file_path:
            return {"path": file_path}
        return {"path": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gpu-info")
async def get_gpu_info():
    info = accelerator_info()
    return {"name": info["name"], "memory": info["memory"], "type": info["type"]}

@app.get("/api/check-scripts")
async def check_scripts():
    internal_scripts = os.path.join(os.path.dirname(__file__), "sd-scripts")
    exists = os.path.exists(os.path.join(internal_scripts, "anima_train_network.py"))
    return {
        "exists": exists,
        "path": internal_scripts if exists else "",
        "setup_running": setup_running,
        "setup_succeeded": setup_succeeded,
    }

@app.post("/api/setup-scripts")
async def setup_scripts():
    global setup_running, setup_succeeded
    internal_scripts = os.path.join(os.path.dirname(__file__), "sd-scripts")
    if setup_running:
        return {"status": "started", "message": "Setup is already running..."}
    
    try:
        setup_running = True
        setup_succeeded = None
        asyncio.create_task(setup_scripts_task(internal_scripts))
        return {"status": "started", "message": "Setup started..."}
    except Exception as e:
        setup_running = False
        setup_succeeded = False
        return {"status": "error", "message": f"Error: {str(e)}"}

async def setup_scripts_task(internal_scripts: str):
    global setup_running, setup_succeeded
    try:
        setup_script = os.path.join(os.path.dirname(__file__), "setup_check.py")
        if not os.path.exists(setup_script):
            setup_succeeded = False
            await broadcast_log(f"Error: {setup_script} not found.\n", "train")
            return

        process = subprocess.Popen(
            [sys.executable, setup_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        await run_and_capture(process, "train")
        
        if process.returncode == 0:
            setup_succeeded = True
            await broadcast_log("\n--- Setup Fully Completed ---\n", "train")
        else:
            setup_succeeded = False
            await broadcast_log("\n--- Setup Failed. Check logs above. ---\n", "train")
            
    except Exception as e:
        setup_succeeded = False
        await broadcast_log(f"Setup Error: {str(e)}\n", "train")
    finally:
        setup_running = False

@app.get("/api/dataset/images")
async def list_images(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    files = []
    for f in os.listdir(path):
        ext = os.path.splitext(f)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            base = os.path.splitext(f)[0]
            txt_path = os.path.join(path, base + ".txt")
            tags = []
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as tf:
                    raw_tags = tf.read().split(",")
                    for t in raw_tags:
                        t = t.strip()
                        if t:
                            tags.append({"name": t, "category": get_tag_category(t)})
            
            files.append({
                "name": f,
                "path": os.path.join(path, f),
                "tags": tags
            })
    return {"files": files}

class TagUpdate(BaseModel):
    path: str
    tags: list[str]

@app.post("/api/dataset/update-tags")
async def update_tags(update: TagUpdate):
    # 'update.path' is the image path, we need the .txt path
    base = os.path.splitext(update.path)[0]
    txt_path = base + ".txt"
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(", ".join(update.tags))
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse
@app.get("/api/image")
async def get_image(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path)

class TaggerConfig(BaseModel):
    path: str
    model: str = ""
    output_dir: str = ""
    name: str = ""
    vram: str = ""
    epochs: int = 1
    lr: str = ""

@app.post("/api/run-tagger")
async def run_tagger(config: TaggerConfig):
    global tagging_logs
    
    tagger_script = os.path.join(os.path.dirname(__file__), "bundled_tagger.py")

    command = [
        sys.executable, tagger_script,
        f"--train_data_dir={config.path}"
    ]
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        asyncio.create_task(run_and_capture(process, "tagger"))
        return {"status": "started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/convert-to-comfy")
async def convert_to_comfy(config: TrainingConfig):
    script_path = os.path.join(os.path.dirname(__file__), "sd-scripts")
    # Source file is in the specified output_dir
    src_path = os.path.join(config.output_dir, f"{config.name}.safetensors")
    dst_path = os.path.join(config.output_dir, f"{config.name}_comfy.safetensors")
    
    if not os.path.exists(src_path):
        return {"status": "error", "message": f"Source file not found: {src_path}"}
        
    convert_script = os.path.join(script_path, "networks", "convert_anima_lora_to_comfy.py")
    if not os.path.exists(convert_script):
        return {"status": "error", "message": f"Conversion script not found: {convert_script}"}

    command = [
        sys.executable, convert_script,
        src_path,
        dst_path
    ]
    
    try:
        process = subprocess.Popen(
            command,
            cwd=script_path,
            env=build_sd_scripts_env(script_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        asyncio.create_task(run_and_capture(process, "convert"))
        return {"status": "started", "output": dst_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def capture_logs(process):
    global training_logs
    for line in iter(process.stdout.readline, ""):
        training_logs += line
        if len(training_logs) > 10000: # Limit log size
            training_logs = training_logs[-10000:]

# Serve frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("APP_PORT", "8000"))
    host = os.environ.get("APP_HOST", "127.0.0.1")
    uvicorn.run(
        app,
        host=host,
        port=port,
        ws_ping_interval=60,
        ws_ping_timeout=60,
        timeout_keep_alive=120,
    )




