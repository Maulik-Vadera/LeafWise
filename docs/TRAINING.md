# Train your own model

The app already includes working starter weights. This optional workflow lets you train on verified data, expand to the 38 original PlantVillage classes and export a compatible model. It does not reproduce the upstream author's exact training run.

## Install training dependencies

In the project folder, after normal setup, use CMD:

```bat
.venv\Scripts\python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install -r training\requirements.txt
```

The CPU path avoids installing an unnecessary CUDA stack. For GPU training, use the [official PyTorch installer](https://pytorch.org/get-started/locally/) and a compatible torch/torchvision pair. Windows data-loader workers default to zero for predictable startup. On Linux/macOS, substitute `.venv/bin/python` in the commands below.

## Obtain and label data

Use [the original PlantVillage repository](https://github.com/spMohanty/PlantVillage-Dataset) or its linked Hugging Face dataset. Review the dataset's current license and attribution. The full repository can be large; allow enough disk space. The app ZIP does not contain the dataset.

For the original repository structure, use the **color images only** and its `leaf_grouping/leaf-map.json`. Do not mix the original, grayscale and segmented copies as though they were independent leaves.

```bat
git clone --depth 1 https://github.com/spMohanty/PlantVillage-Dataset data\PlantVillage
.venv\Scripts\python.exe -m training.import_plantvillage --data data\PlantVillage\raw\color --leaf-map data\PlantVillage\leaf_grouping\leaf-map.json --out data\photos.csv
```

The importer maps capture identifiers to physical-leaf IDs. Unresolved or ambiguous groups cause it to stop and write an audit list. Resolve those from source metadata or curate a verified subset. It deliberately does not pretend that every filename is an independent plant. The importer has not been run across the entire dataset in this delivery.

For your own field data, create `data/photos.csv` yourself:

```csv
path,label,group
plot_a/tomato_001_front.jpg,Tomato___Early_blight,plot_a_plant_001
plot_a/tomato_001_back.jpg,Tomato___Early_blight,plot_a_plant_001
plot_b/tomato_014.jpg,Tomato___healthy,plot_b_plant_014
```

Paths are relative to the image root you supply. Labels must be canonical PlantVillage names or recognized aliases. `app/catalog.py` contains them. The example is only a format illustration: a useful experiment needs many independently labelled plants and enough groups in every class.

Use verified plant/leaf identities for `group`. All views and augmentations of one individual belong together. For a field study, use larger group boundaries such as farm/date blocks where appropriate. A split cannot protect against missing or incorrect metadata.

## Prepare four separate splits

```bat
.venv\Scripts\python.exe -m training.prepare --csv data\photos.csv --root data\PlantVillage\raw\color --out data\splits.csv
```

The script assigns approximately 65% of groups to training, 15% to validation, 10% to calibration and 10% to testing. Per-class counts vary with group sizes. At least four independent groups per class are required for the code to split; that is a technical minimum, not an adequate scientific sample size.

It checks that files stay within the supplied root, rejects conflicting group labels, merges exact decoded-pixel duplicates, and writes split counts. Near duplicates, mislabeled photos and cross-farm leakage still need a separate audit. Augmentation happens only after splitting, during training.

## Train, calibrate and export

```bat
.venv\Scripts\python.exe -m training.train --manifest data\splits.csv --out runs\leafwise_v1 --epochs 15 --batch-size 32
```

The script downloads ImageNet backbone weights on its first normal run. It warms up a new classifier head, fine-tunes the backbone, uses validation loss to choose a checkpoint, and fits a single temperature on the separate calibration split. It exports ONNX, checks numerical agreement with PyTorch, and writes labels, preprocessing, checksums and training history.

Outputs:

| File | Meaning |
|---|---|
| `best.pt` | Locally produced PyTorch state dictionary and labels |
| `model.onnx` | Inference model with embedded weights |
| `manifest.json` | Exact class order, preprocessing, temperature and SHA-256 |
| `training.json` | Epoch history, seed, source-manifest hash and export parity error |

Choose a new empty output directory for each run. The training command will not overwrite an existing experiment. Use `--device cpu` to force CPU, or `--device cuda` with a working GPU install. Reduce batch size if you run out of memory. Training time depends on data size and hardware; no completion-time promise is made.

## Evaluate without tuning on test

```bat
.venv\Scripts\python.exe -m training.evaluate --model runs\leafwise_v1 --manifest data\splits.csv --out runs\leafwise_v1\test_metrics.json
```

The report includes accuracy, per-class precision/recall/F1, confusion matrix, calibration error and the app's acceptance coverage. Accepted accuracy is reported only when at least one sample is accepted. A good result on lab images does not establish good results in fields.

Create a separately reviewed CSV for real field photos with `path,label,group,split`, using `split=field`. Paths for evaluation must be absolute or relative to the current working directory. Evaluate it with `--split field`. Do not reuse it to tune the model and keep calling it a test set.

To inspect false acceptance of unsupported plants and non-leaf objects:

```bat
.venv\Scripts\python.exe -m training.evaluate --model runs\leafwise_v1 --manifest data\splits.csv --out runs\leafwise_v1\test_with_unknowns.json --unknown-root data\unknowns
```

This is an evaluation tool, not a trained rejection system. It deliberately measures the case where a user wrongly confirms the model's crop guess. It does not silently declare unfamiliar images safe or correct.

## Activate an evaluated model

Set `MODEL_DIR=runs/leafwise_v1` in `.env` and restart Leafwise. Leave the bundled `models` folder as a fallback. The model loader checks hashes, input dimensions and output-label counts before serving predictions. Review new care cards before using a larger class set with farmers.

## A strong next research project

Improve field reliability before adding more labels. Collect independent images with farmer consent, verified pathology labels, multiple seasons, different devices and realistic backgrounds. Compare lab-to-field performance and per-crop errors. Add a learned leaf/plant detector and out-of-distribution rejection. For cultivar recognition, first choose a small set of visually distinguishable, well-documented varieties and gather multi-organ, expert-labelled examples. Universal cultivar identification from one leaf is not a defensible goal.
