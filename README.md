# Anima LoRA Factory 🚀

<img src="https://github.com/UNfukashigi/Anima-LoRA-Factory/blob/main/image1.png">

Anima LoRA Factory は、次世代画像生成モデル Anima の LoRA 学習を、プログラミングの知識なしで誰でも簡単に行えるように設計された GUI ツールです。 特に最新の NVIDIA RTX 50シリーズ (Blackwell / sm_120) への対応や、複雑な環境構築の自動化にこだわっています。

> Anima LoRA Factory is a user-friendly GUI tool designed for training LoRAs for the next-generation Anima diffusion models. It simplifies the complex setup process and offers native support for the latest NVIDIA RTX 50 Series (Blackwell / sm_120) GPUs.

## 📥 ダウンロード / Download

👉 **[最新版をダウンロード / Download Latest Release](https://github.com/UNfukashigi/Anima-LoRA-Factory/releases/latest)**

▼SDXLバージョンも公開しています。- SDXL version is also available.<br>
[https://github.com/UNfukashigi/SDXL-LoRA-Factory](https://github.com/UNfukashigi/SDXL-LoRA-Factory)

▼詳しい使い方については、以下の記事をご覧ください。- For detailed instructions on how to use it, please see the article below.<br>
[https://x.com/UNfukashigi/status/2045744319433490449](https://x.com/UNfukashigi/status/2045744319433490449)

---

## 🌟 主な機能 / Key Features

### ✅全自動環境構築 / Auto Setup

Windows は `start.bat`、Ubuntu / macOS は `./start.sh` を実行するだけで、必要な学習エンジン (sd-scripts) と OS / GPU に合った PyTorch を自動的にセットアップします。<br>
Run `start.bat` on Windows or `./start.sh` on Ubuntu/macOS to set up the training engine and a suitable PyTorch build automatically.

### ✅ビジュアルタグエディタ / Visual Tag Editor

画像を見ながら直感的にキャプション（タグ）を編集可能。WD14 Tagger による自動タグ付け機能も内蔵しています。 トリガーワードも簡単に追加できます。<br>
Edit captions/tags intuitively while viewing your images. Built-in automatic tagging with WD14 Tagger is also included.Trigger words can also be easily added.

### ✅リアルタイム進捗 / Real-time Progress

学習の進捗状況をプログレスバーとブラウザのタブタイトルでリアルタイムに確認できます。<br>
Check training progress in real time through the progress bar and the browser tab title.

### ✅学習履歴 / Training History

過去の学習設定を自動で保存し、あとから確認できます。素材フォルダ、推定ステップ数、主要な学習設定、@付きトリガーワードなどを直近30件まで記録します。<br>
Automatically saves past training settings so you can review them later. It records up to the latest 30 runs, including dataset folder, estimated steps, key training settings, and @ trigger words.

### ✅Blackwell (RTX 50) 対応 / Blackwell Ready

最新GPUで発生しがちな CUDA エラーを自動検知し、最適な環境（CUDA 13.0 等）を構成します。<br>
Automatically detects common CUDA issues on the latest GPUs and configures an optimized environment, such as CUDA 13.0.

### ✅自動シャットダウン / Auto Shutdown

長時間の学習完了後に PC を自動でシャットダウンするオプションを搭載。<br>
Includes an option to automatically shut down your PC after long training sessions finish.

### ✅ComfyUI 変換機能 / ComfyUI Conversion

学習完了後、自動的に ComfyUI で即座に使用可能な形式へ変換・出力します。  
After training completes, the LoRA is automatically converted and exported into a format that can be used immediately in ComfyUI.

---

## 📋 動作要件 / Requirements

- Python 3.10 / 3.11 / 3.12 (64-bit; 3.10 recommended)
- 次のいずれか / One of:
  - Ubuntu 22.04 以降 + NVIDIA GPU + 最新の NVIDIA ドライバー
  - Windows 10 / 11 64-bit + NVIDIA GPU
  - Apple Silicon Mac + PyTorch MPS 対応 macOS（実験的対応）

CPU のみでの学習は非常に遅いため、誤操作防止のため開始しません。macOS 版は Apple Metal (MPS) を使いますが、CUDA 版よりメモリ制約が厳しく、sd-scripts 側の未対応 MPS 演算に遭遇する場合があります。PyTorch の [MPS バックエンド](https://docs.pytorch.org/docs/stable/notes/mps.html) も参照してください。

Python 3.10〜3.12 が見つからない場合、[`uv`](https://docs.astral.sh/uv/) がインストール済みなら `start.sh` が Python 3.12 を自動用意します。

### 🔧 必要モデル / Required Models

- **Anima Base Model**
  - `anima-base-v1.0.safetensors`
  - https://huggingface.co/circlestone-labs/Anima/blob/main/split_files/diffusion_models/anima-base-v1.0.safetensors 
  - 派生モデルでの学習は動作保証していません。Training with derivative models is not officially supported.

- **Qwen3 Text Encoder**
  - `qwen_3_06b_base.safetensors`
  - https://huggingface.co/circlestone-labs/Anima/blob/main/split_files/text_encoders/qwen_3_06b_base.safetensors

- **Qwen Image VAE**
  - `qwen_image_vae.safetensors`
  - https://huggingface.co/circlestone-labs/Anima/blob/main/split_files/vae/qwen_image_vae.safetensors

## 🚀 使い方

### Ubuntu

```bash
sudo apt update
sudo apt install python3-venv python3-tk
chmod +x start.sh
./start.sh
```

NVIDIA ドライバーが認識されていることは `nvidia-smi` で確認できます。ブラウザを自動で開かないサーバーでは `NO_BROWSER=1 ./start.sh` とし、表示された URL を開いてください。サーバーは安全のため初期値で localhost のみに待ち受けます。LAN からの利用を明示的に許可する場合のみ `APP_HOST=0.0.0.0 ./start.sh` を使い、ファイアウォールでポートを制限してください。

### macOS

Command Line Tools と Python 3.10〜3.12 を用意し、Terminal で次を実行します。

```bash
chmod +x start.sh
./start.sh
```

### Windows

`start.bat` をダブルクリックします。

初回は `venv` の作成と依存関係の取得に時間がかかります。完了後、画像フォルダと Anima Base Model / VAE / Qwen3 の各パスを GUI で指定し、「LoRA学習開始」を押します。フォルダ選択ダイアログが使えないヘッドレス環境ではパスを直接入力できます。

## 🚀 How to Use

On Ubuntu or macOS, run `chmod +x start.sh && ./start.sh`. On Windows, double-click `start.bat`. The launcher creates an isolated environment, installs the platform-specific PyTorch build and dependencies, then opens the browser GUI. Set the dataset, base model, VAE, Qwen3, and output paths and click **Start Training**.

---

## 📝 更新履歴 / Version History

v4.7以降の更新内容は **Releases**、それ以前の更新履歴は **CHANGELOG.md** をご覧ください。  
For version history, see **Releases** for v4.7 and later, and **CHANGELOG.md** for earlier versions.

- [Releases](https://github.com/UNfukashigi/Anima-LoRA-Factory/releases)
- [CHANGELOG.md](CHANGELOG.md)

---

## 🔗 参考・クレジット / References & Credits
このプロジェクトは、以下の素晴らしいリポジトリおよびモデルの成果に基づいています。

- Anima Model: [circlestone-labs/Anima (HuggingFace)](https://huggingface.co/circlestone-labs/Anima)
- Training Engine: [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)
- Anima Training Docs: [sd-scripts/anima_train_network.md](https://github.com/kohya-ss/sd-scripts/blob/main/docs/anima_train_network.md)

## 🔑License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 📝 免責事項 / Disclaimer
本ツールを使用して作成されたモデルや、その使用によって生じた損害について、開発者は一切の責任を負いません。 The developer is not responsible for any models created using this tool or any damage caused by its use.

---

Created by [fukachan.jp](https://fukachan.jp/)<br>

X [https://x.com/UNfukashigi](https://x.com/UNfukashigi)
