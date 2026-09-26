

let datasetImageCount = 0;

// Tab handling
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const tab = item.getAttribute('data-tab');
        
        // Update nav
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        
        // Update content
        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        document.getElementById(`tab-${tab}`).style.display = 'block';
    });
});

async function browseFolder() {
    const response = await fetch('/api/browse-folder');
    const data = await response.json();
    if (data.path) {
        document.getElementById('dataset-path').value = data.path;
        refreshDatasetImageCount();
    }
}

async function browseFile(inputId, titleStr) {
    const response = await fetch(`/api/browse-file?title=${encodeURIComponent(titleStr)}`);
    const data = await response.json();
    if (data.path) {
        const input = document.getElementById(inputId);
        input.value = data.path;
        localStorage.setItem(`anima_factory_${inputId}`, data.path);
    }
}

async function browseOutput() {
    const response = await fetch('/api/browse-folder');
    const data = await response.json();
    if (data.path) {
        const input = document.getElementById('output-dir');
        input.value = data.path;
        localStorage.setItem('anima_factory_OutputDir', data.path);
    }
}

function toggleAdvancedSettings() {
    const isChecked = document.getElementById('enable-advanced').checked;
    const container = document.getElementById('advanced-settings-container');
    container.style.display = isChecked ? 'flex' : 'none';
}

function toggleOptimizerSettings() {
    const optimizerType = document.getElementById('optimizer-type').value;
    const isCustom = optimizerType !== 'AdamW';

    document.getElementById('lr-adamw-section').style.display = isCustom ? 'none' : 'block';
    document.getElementById('lr-prodigy-section').style.display = isCustom ? 'block' : 'none';
    document.getElementById('optimizer-low-vram-section').style.display = isCustom ? 'block' : 'none';
}

function toggleAdvancedOptionInputs() {
    const shuffleCaption = document.getElementById('shuffle-caption');
    const keepTokens = document.getElementById('keep-tokens');
    const minSnrGamma = document.getElementById('min-snr-gamma');
    const minSnrGammaValue = document.getElementById('min-snr-gamma-value');

    if (shuffleCaption && keepTokens) {
        keepTokens.disabled = !shuffleCaption.checked;
    }
    if (minSnrGamma && minSnrGammaValue) {
        minSnrGammaValue.disabled = !minSnrGamma.checked;
    }
}

async function loadGPUInfo() {
    try {
        const response = await fetch('/api/gpu-info');
        const data = await response.json();
        const display = document.getElementById('gpu-info-display');
        if (display) {
            display.innerText = `${data.name} (VRAM: ${data.memory})`;
        }
    } catch (e) {
        console.error("Failed to load GPU info", e);
    }
}

async function checkScriptsStatus() {
    const response = await fetch('/api/check-scripts');
    const data = await response.json();
    if (data.exists) {
        const btn = document.getElementById('setup-scripts-btn');
        btn.innerText = '✅ エンジン取得済み（再インストール可能） / Ready (click to reinstall deps)';
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.background = 'rgba(52, 211, 153, 0.2)';
        btn.style.borderColor = '#34d499';
    }
}

async function setupScripts() {
    const btn = document.getElementById('setup-scripts-btn');
    const progressText = document.getElementById('setup-progress-text');
    btn.disabled = true;
    btn.innerText = 'セットアップ中... (Setting up...)';
    
    if (progressText) {
        progressText.style.display = 'block';
    }

    try {
        const response = await fetch('/api/setup-scripts', { method: 'POST' });
        const data = await response.json();
        if (data.status === 'started' || data.status === 'exists') {
            // Poll for completion
            let attempts = 0;
            const maxAttempts = 600; // dependency repair can take up to 30 minutes
            const interval = setInterval(async () => {
                attempts++;
                const checkRes = await fetch('/api/check-scripts');
                const checkData = await checkRes.json();
                
                if (!checkData.setup_running && checkData.setup_succeeded === true) {
                    clearInterval(interval);
                    btn.innerText = '✅ 取得完了！ (Success)';
                    if (progressText) progressText.innerText = '✅ セットアップが完了しました。 / Setup completed successfully.';
                    checkScriptsStatus(); // Update button UI
                    alert('エンジンの自動取得が完了しました！ / Engine setup completed!');
                } else if (!checkData.setup_running && checkData.setup_succeeded === false) {
                    clearInterval(interval);
                    btn.disabled = false;
                    btn.innerText = '❌ セットアップ失敗 (Setup failed)';
                    if (progressText) progressText.innerText = '❌ セットアップに失敗しました。ログを確認してください。';
                } else if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    btn.disabled = false;
                    btn.innerText = '❌ タイムアウト (Timeout)';
                    if (progressText) progressText.innerText = '❌ 取得に時間がかかりすぎています。コンソールを確認してください。';
                    alert('エンジンの確認がタイムアウトしました。');
                }
            }, 3000);
        } else {
            alert('Error: ' + data.message);
            btn.disabled = false;
            btn.innerText = '❌ 取得失敗 (Failed)';
            if (progressText) progressText.innerText = '❌ エラーが発生しました。Gitがインストールされているか確認してください。 / Error occurred. Please check if Git is installed.';
        }
    } catch (e) {
        alert('Error: ' + e.message);
        btn.disabled = false;
        btn.innerText = '学習エンジンの自動取得 (Setup sd-scripts)';
        if (progressText) progressText.style.display = 'none';
    }
}

// Check on load
window.addEventListener('DOMContentLoaded', () => {
    checkScriptsStatus();
    loadGPUInfo();
    
    // Load saved paths
    const savedModel = localStorage.getItem('anima_factory_ModelPath');
    const savedOutput = localStorage.getItem('anima_factory_OutputDir');
    if (savedModel) document.getElementById('model-path').value = savedModel;
    if (savedOutput) document.getElementById('output-dir').value = savedOutput;

    // Add event listeners to save on manual typing
    document.getElementById('model-path')?.addEventListener('change', (e) => localStorage.setItem('anima_factory_ModelPath', e.target.value));
    document.getElementById('output-dir')?.addEventListener('change', (e) => localStorage.setItem('anima_factory_OutputDir', e.target.value));
});


function updateTrainingStrengthEstimate() {
    const epochsInput = document.getElementById('epochs');
    const repeatsInput = document.getElementById('repeats');
    const totalEl = document.getElementById('estimated-steps');
    const detailEl = document.getElementById('step-estimate-detail');

    if (!epochsInput || !repeatsInput || !totalEl || !detailEl) return;

    const epochs = Math.max(parseInt(epochsInput.value, 10) || 0, 0);
    const repeats = Math.max(parseInt(repeatsInput.value, 10) || 0, 0);
    const totalSteps = datasetImageCount * repeats * epochs;

    if (!datasetImageCount) {
        totalEl.innerText = '推定: -- steps';
        detailEl.innerText = '画像枚数を読み込むと推定ステップ数を表示します。';
        return;
    }

    totalEl.innerText = `推定: ${totalSteps.toLocaleString()} steps`;
    detailEl.innerText = `${datasetImageCount}枚 × Repeats ${repeats} × Epochs ${epochs} = 約 ${totalSteps.toLocaleString()} steps`;
}

async function refreshDatasetImageCount() {
    const datasetPath = document.getElementById('dataset-path')?.value;
    if (!datasetPath) {
        datasetImageCount = 0;
        updateTrainingStrengthEstimate();
        return;
    }

    try {
        const response = await fetch(`/api/dataset/images?path=${encodeURIComponent(datasetPath)}`);
        const data = await response.json();
        datasetImageCount = Array.isArray(data.files) ? data.files.length : 0;
    } catch (e) {
        datasetImageCount = 0;
    }

    updateTrainingStrengthEstimate();
}
function validatePath() {
    const path = document.getElementById('dataset-path').value;
    if (!path) {
        alert('パスを入力してください / Please enter a path');
        return;
    }
    // Switch to tagger tab instead of config
    document.querySelector('.nav-item[data-tab="tagger"]').click();
    loadDataset(path);
}

async function loadDataset(path) {
    const container = document.getElementById('tag-editor-content');
    container.innerHTML = '<p>Loading dataset...</p>';
    
    try {
        const response = await fetch(`/api/dataset/images?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        
        container.innerHTML = '';
        datasetImageCount = Array.isArray(data.files) ? data.files.length : 0;
        updateTrainingStrengthEstimate();
        data.files.forEach(file => {
            const card = createTagCard(file);
            container.appendChild(card);
        });
        updateTagSuggestions();
    } catch (e) {
        datasetImageCount = 0;
        updateTrainingStrengthEstimate();
        container.innerHTML = `<p style="color: red;">Error: ${e.message}</p>`;
    }
}

function updateTagSuggestions() {
    const datalist = document.getElementById('tag-suggestions');
    if (!datalist) return;

    const allTags = new Set();
    document.querySelectorAll('.tag-chip').forEach(chip => {
        const tag = chip.getAttribute('data-tag');
        if (tag) allTags.add(tag);
    });

    datalist.innerHTML = '';
    Array.from(allTags).sort().forEach(tag => {
        const option = document.createElement('option');
        option.value = tag;
        datalist.appendChild(option);
    });
}

function createTagCard(file) {
    const card = document.createElement('div');
    card.className = 'card image-tag-card';
    
    // Use the proxy API for local images
    const imgUrl = `/api/image?path=${encodeURIComponent(file.path)}`;
    
    card.innerHTML = `
        <img src="${imgUrl}" class="tag-preview-img">
        <div class="tags-container" data-path="${file.path}">
            ${file.tags.map(tag => `
                <span class="tag-chip ${tag.category}" data-tag="${tag.name}">
                    ${tag.name} <span class="remove-btn" onclick="removeTag(this)">×</span>
                </span>
            `).join('')}
            <input type="text" class="add-tag-input" placeholder="+ Add" onkeydown="handleTagInput(event, this)">
        </div>
    `;
    return card;
}

function removeTag(el) {
    const chip = el.parentElement;
    const container = chip.parentElement;
    chip.remove();
    saveTags(container);
    updateTagSuggestions();
}

function handleTagInput(event, input) {
    if (event.key === 'Enter') {
        const val = input.value.trim();
        if (val) {
            const container = input.parentElement;
            const chip = document.createElement('span');
            // Simple logic for category on the fly
            const category = val.startsWith('@') ? 'tag-char' : 'tag-general';
            chip.className = `tag-chip ${category}`;
            chip.setAttribute('data-tag', val);
            chip.innerHTML = `${val} <span class="remove-btn" onclick="removeTag(this)">×</span>`;
            container.insertBefore(chip, input);
            input.value = '';
            saveTags(container);
            updateTagSuggestions();
        }
    }
}

async function saveTags(container) {
    const path = container.getAttribute('data-path');
    const tags = Array.from(container.querySelectorAll('.tag-chip')).map(c => c.getAttribute('data-tag'));
    
    await fetch('/api/dataset/update-tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, tags })
    });
}

async function batchAddTags() {
    await batchAddTagsAtPosition('append');
}

async function batchAddTriggerWords() {
    await batchAddTagsAtPosition('prepend');
}

function createTagChip(tag) {
    const chip = document.createElement('span');
    const category = tag.startsWith('@') ? 'tag-char' : 'tag-general';
    chip.className = `tag-chip ${category}`;
    chip.setAttribute('data-tag', tag);
    chip.innerHTML = `${tag} <span class="remove-btn" onclick="removeTag(this)">&times;</span>`;
    return chip;
}

async function batchAddTagsAtPosition(position) {
    const input = document.getElementById('batch-tags-input');
    const tags = [...new Set(input.value.split(',').map(t => t.trim()).filter(t => t))];
    if (tags.length === 0) {
        alert('タグを入力してください / Please enter tags');
        return;
    }

    const containers = document.querySelectorAll('.tags-container');
    let totalAdded = 0;
    for (const container of containers) {
        if (container.closest('.placeholder-card')) continue;

        const currentTags = new Set(Array.from(container.querySelectorAll('.tag-chip')).map(c => c.getAttribute('data-tag')));
        let addedInCard = false;
        const tagsToAdd = tags.filter(tag => !currentTags.has(tag));

        if (position === 'prepend') {
            let referenceNode = container.querySelector('.tag-chip') || container.querySelector('.add-tag-input');
            tagsToAdd.slice().reverse().forEach(tag => {
                const chip = createTagChip(tag);
                container.insertBefore(chip, referenceNode);
                referenceNode = chip;
                addedInCard = true;
                totalAdded++;
                currentTags.add(tag);
            });
        } else {
            const inputEl = container.querySelector('.add-tag-input');
            tagsToAdd.forEach(tag => {
                const chip = createTagChip(tag);
                container.insertBefore(chip, inputEl);
                addedInCard = true;
                totalAdded++;
                currentTags.add(tag);
            });
        }
        if (addedInCard) {
            await saveTags(container);
        }
    }
    updateTagSuggestions();
    const actionLabel = position === 'prepend' ? 'Trigger word add' : 'Batch add';
    alert(`一括追加が完了しました（${totalAdded}個のタグを追加） / ${actionLabel} completed (${totalAdded} tags added)`);
}

async function batchRemoveTags() {
    const input = document.getElementById('batch-tags-input');
    const tags = input.value.split(',').map(t => t.trim()).filter(t => t);
    if (tags.length === 0) {
        alert('タグを入力してください / Please enter tags');
        return;
    }

    const containers = document.querySelectorAll('.tags-container');
    let totalRemoved = 0;
    for (const container of containers) {
        if (container.closest('.placeholder-card')) continue;

        let removedInCard = false;
        tags.forEach(tag => {
            const chips = container.querySelectorAll(`.tag-chip[data-tag="${tag}"]`);
            if (chips.length > 0) {
                chips.forEach(c => {
                    c.remove();
                    totalRemoved++;
                });
                removedInCard = true;
            }
        });
        if (removedInCard) {
            await saveTags(container);
        }
    }
    updateTagSuggestions();
    alert(`一括削除が完了しました（${totalRemoved}個のタグを削除） / Batch remove completed (${totalRemoved} tags removed)`);
}

async function runAutoTagging() {
    const btn = document.getElementById('run-tagger-btn');
    const path = document.getElementById('dataset-path').value;
    
    if (!path) {
        alert('パスを入力してください / Please enter a path');
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerText = 'タグ付け実行中... / Tagging...';
    }
    
    // Show progress bar
    const progressContainer = document.getElementById('tagger-progress-container');
    if (progressContainer) {
        progressContainer.style.display = 'block';
        document.getElementById('tagger-progress-percent').innerText = '0%';
        document.getElementById('tagger-progress-bar').style.width = '0%';
        document.getElementById('tagger-progress-text').innerText = 'タグ付け進捗: 準備中... / Tagging Progress: Preparing...';
    }

    connectWebSocket();

    try {
        const response = await fetch('/api/run-tagger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                path: path, 
                model: document.getElementById('model-path').value || '',
                output_dir: '',
                name: 'tagger_job',
                vram: 'balanced',
                epochs: 1,
                lr: '0'
            })
        });
        
        const data = await response.json();
        if (data.status === 'started') {
            console.log("Tagger started...");
        } else {
            const errorMsg = data.message || (data.detail ? JSON.stringify(data.detail) : "Unknown error");
            alert("Error: " + errorMsg);
            if (btn) {
                btn.disabled = false;
                btn.innerText = '自動タグ付け実行 / Run Tagger';
            }
        }
    } catch (e) {
        alert("Error: " + e.message);
        if (btn) {
            btn.disabled = false;
            btn.innerText = '自動タグ付け実行 / Run Tagger';
        }
    }
}

// Add a refresh button or logic
async function refreshDataset() {
    const path = document.getElementById('dataset-path').value;
    if (path) {
        loadDataset(path);
    }
}

async function startTraining() {
    const consoleOut = document.getElementById('console-output');
    consoleOut.innerHTML = '学習プロセスを開始しています...<br>';

    // Switch to train tab
    document.querySelector('.nav-item[data-tab="train"]').click();

    const optimizerType = document.getElementById('optimizer-type').value;
    const isCustomOptimizer = optimizerType !== 'AdamW';
    const lr = isCustomOptimizer
        ? document.getElementById('prodigy-lr').value
        : document.querySelector('input[name="learning-rate"]:checked').value;

    try {
        const response = await fetch('/api/start-training', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: document.getElementById('dataset-path').value,
                model: document.getElementById('model-path').value,
                vae: document.getElementById('vae-path').value,
                qwen3: document.getElementById('qwen-path').value,
                output_dir: document.getElementById('output-dir').value,
                name: document.getElementById('output-name').value,
                vram: document.getElementById('vram-mode').value,
                epochs: parseInt(document.getElementById('epochs').value) || 10,
                repeats: parseInt(document.getElementById('repeats').value) || 2,
                lr: lr,
                rank: parseInt(document.getElementById('lora-rank').value) || 4,
                alpha: parseInt(document.getElementById('lora-alpha').value) || 1,
                flip_aug: document.getElementById('flip-aug').checked,
                shuffle_caption: document.getElementById('shuffle-caption').checked,
                keep_tokens: parseInt(document.getElementById('keep-tokens').value) || 0,
                min_snr_gamma: document.getElementById('min-snr-gamma').checked,
                min_snr_gamma_value: parseFloat(document.getElementById('min-snr-gamma-value').value) || 5,
                keep_unet: document.getElementById('keep-unet').checked,
                shutdown: document.getElementById('auto-shutdown').checked,
                optimizer_type: optimizerType,
                optimizer_args: document.getElementById('optimizer-args').value,
                optimizer_low_vram: document.getElementById('optimizer-low-vram').checked,
                dataloader_workers: parseInt(document.getElementById('dataloader-workers').value) || 0
            })
        });
        
        const data = await response.json();
        if (data.status === 'started') {
            connectWebSocket();
            // Disable UI
            document.getElementById('start-train-btn').disabled = true;
            document.getElementById('start-train-btn').innerText = '学習準備中... / Preparing...';
            document.getElementById('keep-unet').disabled = true;
            document.getElementById('auto-shutdown').disabled = true;
        } else {
            consoleOut.innerHTML += `<span style="color: #ef4444;">Error: ${data.message}</span>`;
        }
    } catch (e) {
        consoleOut.innerHTML += `<span style="color: #ef4444;">Error: ${e.message}</span>`;
    }
}

async function convertToComfy() {
    const consoleOut = document.getElementById('console-output');
    consoleOut.innerHTML += '<br>ComfyUI形式への変換を開始します...<br>';
    connectWebSocket();

    try {
        const response = await fetch('/api/convert-to-comfy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: document.getElementById('dataset-path').value,
                name: document.getElementById('output-name').value,
                vram: document.getElementById('vram-mode').value,
                epochs: document.getElementById('epochs').value,
                lr: document.getElementById('learning-rate').value
            })
        });
        
        const data = await response.json();
        if (data.status === 'started') {
            console.log("Conversion started...");
        } else {
            consoleOut.innerHTML += `<span style="color: #ef4444;">Error: ${data.message}</span>`;
        }
    } catch (e) {
        consoleOut.innerHTML += `<span style="color: #ef4444;">Error: ${e.message}</span>`;
    }
}



function escapeHistoryText(value) {
    return String(value ?? '-').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[char]));
}
function formatHistoryDate(value) {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function renderTrainingHistory(items) {
    const content = document.getElementById('history-content');
    if (!content) return;

    if (!Array.isArray(items) || items.length === 0) {
        content.innerHTML = '<p class="history-empty">まだ学習履歴がありません。<br>No training history yet.</p>';
        return;
    }

    const renderFields = (fields, extraClass = '') => fields.map(([label, value]) => `
        <div class="history-field ${extraClass}">
            <span>${escapeHistoryText(label)}</span>
            <strong>${escapeHistoryText(value)}</strong>
        </div>
    `).join('');

    content.innerHTML = items.map(item => {
        const settings = item.settings || {};
        const advancedFields = [
            ['DataLoader Workers', settings.dataloader_workers ?? 0],
            ['左右反転 / Flip Aug', settings.flip_aug ? 'ON' : 'OFF'],
            ['タグ順シャッフル / Shuffle Caption', settings.shuffle_caption ? `ON / keep ${settings.keep_tokens ?? 0}` : 'OFF'],
            ['Min SNR Gamma', settings.min_snr_gamma ? `ON / ${settings.min_snr_gamma_value ?? 5}` : 'OFF'],
            ['Optimizer Args', settings.optimizer_args || '-'],
            ['低VRAM Optimizer', settings.optimizer_low_vram ? 'ON' : 'OFF'],
            ['自動シャットダウン / Auto Shutdown', settings.shutdown ? 'ON' : 'OFF']
        ];
        if (Object.prototype.hasOwnProperty.call(settings, 'keep_unet')) {
            advancedFields.splice(6, 0, ['Keep UNET', settings.keep_unet ? 'ON' : 'OFF']);
        }

        const triggerWords = Array.isArray(item.trigger_words) ? item.trigger_words.filter(Boolean) : [];
        const mainFields = [
            ['素材フォルダ', item.dataset_path || '-'],
            ['出力先', item.output_dir || '-'],
            ['画像枚数', `${item.image_count ?? 0}枚`],
            ['推定ステップ', `${item.estimated_steps ?? 0} steps`],
            ['Epochs / Repeats', `${settings.epochs ?? '-'} / ${settings.repeats ?? '-'}`],
            ['学習率', settings.lr || '-'],
            ['Rank / Alpha', `${settings.rank ?? '-'} / ${settings.alpha ?? '-'}`],
            ['VRAM', settings.vram || '-'],
            ['Optimizer', settings.optimizer_type || 'AdamW']
        ];
        if (triggerWords.length) {
            mainFields.splice(4, 0, ['トリガーワード', triggerWords.join(', ')]);
        }

        return `
            <article class="history-entry">
                <div class="history-entry-header">
                    <div class="history-entry-title">${escapeHistoryText(item.name || '(no name)')}</div>
                    <div class="history-entry-date">${escapeHistoryText(formatHistoryDate(item.started_at))}</div>
                </div>
                <div class="history-grid">
                    ${renderFields(mainFields)}
                </div>
                <div class="history-advanced">
                    <div class="history-section-title">上級設定 / Advanced Settings</div>
                    <div class="history-grid history-grid-advanced">
                        ${renderFields(advancedFields, 'history-field-advanced')}
                    </div>
                </div>
            </article>
        `;
    }).join('');
}
async function openTrainingHistory() {
    const modal = document.getElementById('history-modal');
    const content = document.getElementById('history-content');
    if (!modal || !content) return;

    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    content.innerHTML = '<p class="history-empty">履歴を読み込み中です...</p>';

    try {
        const response = await fetch('/api/training-history');
        const data = await response.json();
        renderTrainingHistory(data.history || []);
    } catch (e) {
        content.innerHTML = `<p class="history-empty">履歴を読み込めませんでした。<br>${e.message}</p>`;
    }
}

function closeTrainingHistory() {
    const modal = document.getElementById('history-modal');
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
}
function connectWebSocket() {
    const consoleOut = document.getElementById('console-output');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
    
    ws.onmessage = (event) => {
        const data = event.data.trim();
        // Append log line
        const line = document.createElement('div');
        line.innerText = data;
        consoleOut.appendChild(line);
        consoleOut.scrollTop = consoleOut.scrollHeight;

        if (data.includes("[TAGGER_PROGRESS]")) {
            const match = data.match(/\[TAGGER_PROGRESS\]\s+(\d+)\/(\d+)/);
            if (match) {
                const current = parseInt(match[1]);
                const total = parseInt(match[2]);
                const percent = Math.round((current / total) * 100);
                
                const progressText = document.getElementById('tagger-progress-text');
                const progressPercent = document.getElementById('tagger-progress-percent');
                const progressBar = document.getElementById('tagger-progress-bar');
                
                if (progressText) {
                    progressText.innerText = `タグ付け進捗 / Tagging Progress: ${current} / ${total}`;
                    progressPercent.innerText = `${percent}%`;
                    progressBar.style.width = `${percent}%`;
                }
                
                if (current === total) {
                    setTimeout(() => {
                        refreshDataset();
                        document.getElementById('tagger-progress-container').style.display = 'none';
                        const btn = document.querySelector('#tab-tagger .btn-primary:last-child');
                        if (btn) {
                            btn.disabled = false;
                            btn.innerText = '自動タグ付け実行 / Run Tagger';
                        }
                    }, 1000);
                }
            }
        }

        if (data.includes("steps:")) {
            const match = data.match(/steps:\s+(\d+)%\|.*\| (\d+)\/(\d+)/);
            if (match) {
                const percent = match[1];
                const current = match[2];
                const total = match[3];
                
                // Update button
                const btn = document.getElementById('start-train-btn');
                if (btn) {
                    btn.innerText = `学習中 / Training: ${percent}% (${current}/${total})`;
                }
                
                // Update page title
                document.title = `(${percent}%) Anima LoRA Factory`;
            }
        }

        if (data.includes("--- TRAIN Finished ---") || data.includes("All Processes Finished Successfully")) {
            const btn = document.getElementById('start-train-btn');
            if (btn) {
                btn.disabled = false;
                btn.innerText = '🚀 LoRA学習開始 / Start Training';
            }
            document.getElementById('keep-unet').disabled = false;
            document.getElementById('auto-shutdown').disabled = false;
            
            // Reset title
            document.title = "Anima LoRA Factory";
        }
    };
    
    ws.onclose = () => {
        consoleOut.innerHTML += '<br>--- WebSocket Disconnected ---';
    };
}

document.addEventListener('DOMContentLoaded', () => {
    localStorage.removeItem('anima_factory_optimizer-args');
    const optimizerArgs = document.getElementById('optimizer-args');
    if (optimizerArgs) optimizerArgs.value = '';

    ['dataset-path', 'model-path', 'vae-path', 'qwen-path', 'output-dir', 'lora-rank', 'lora-alpha', 'repeats', 'epochs', 'dataloader-workers', 'keep-tokens', 'min-snr-gamma-value', 'optimizer-type'].forEach(id => {
        const saved = localStorage.getItem('anima_factory_' + id);
        const el = document.getElementById(id);
        if (saved && el) el.value = saved;
        if (el) {
            el.addEventListener('change', (e) => {
                localStorage.setItem('anima_factory_' + id, e.target.value);
            });
        }
    });

    ['keep-unet', 'auto-shutdown', 'enable-advanced', 'optimizer-low-vram', 'flip-aug', 'shuffle-caption', 'min-snr-gamma'].forEach(id => {
        const saved = localStorage.getItem('anima_factory_' + id);
        const el = document.getElementById(id);
        if (saved !== null && el) {
            el.checked = saved === 'true';
            if (id === 'enable-advanced') {
                toggleAdvancedSettings();
            }
            if (id === 'shuffle-caption' || id === 'min-snr-gamma') {
                toggleAdvancedOptionInputs();
            }
        }
        if (el) {
            el.addEventListener('change', () => {
                localStorage.setItem('anima_factory_' + id, el.checked);
                if (id === 'shuffle-caption' || id === 'min-snr-gamma') {
                    toggleAdvancedOptionInputs();
                }
            });
        }
    });

    document.getElementById('epochs')?.addEventListener('input', updateTrainingStrengthEstimate);
    document.getElementById('repeats')?.addEventListener('input', updateTrainingStrengthEstimate);
    document.getElementById('dataset-path')?.addEventListener('change', refreshDatasetImageCount);
    refreshDatasetImageCount();

    document.getElementById('history-modal')?.addEventListener('click', (event) => {
        if (event.target.id === 'history-modal') closeTrainingHistory();
    });

    toggleOptimizerSettings();
    toggleAdvancedOptionInputs();
});




