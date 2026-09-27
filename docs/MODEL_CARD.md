# Included model card

| Item | Value |
|---|---|
| Source | [imaflower/plantvillage-mobilenetv3](https://huggingface.co/imaflower/plantvillage-mobilenetv3) |
| Pinned revision | `d76fe187be1c4c3a5474f835a7a70cd08c7ab085` |
| Architecture | MobileNetV3 small, according to upstream training configuration |
| Model name in app | MobileNetV3 · PlantVillage starter |
| Label count | 15, with exact order in `models/manifest.json` |
| Crop coverage | Bell pepper, potato, tomato |
| Input | RGB, NCHW float32, 224×224 |
| Normalization | Mean `[0.485,0.456,0.406]`; std `[0.229,0.224,0.225]` |
| Resizing | Short side 256, centre crop 224, bilinear |
| Runtime | ONNX Runtime, CPU |
| Redistribution license | MIT declared by upstream repository metadata |
| Independent field validation | None performed |
| Confidence calibration | Starter temperature 1.0; uncalibrated |
| Decision defaults | Score ≥0.85 and top-two margin ≥0.25, plus matching known crop, usable capture and agreeing views |

The upstream model-card prose contains unresolved template placeholders and a size inconsistency. This implementation uses the concrete `img_size=224` value from `training_config.json`, confirms the ONNX input shape, and follows the example's resize/crop and normalization path. The raw upstream class names are retained in `class_names.json`, while the application manifest stores the corresponding canonical labels.

The upstream author reports high evaluation accuracy on curated data. That claim was not independently reproduced. It is deliberately not presented as Leafwise's accuracy or as evidence of farm reliability. Three sample photos were used to check inference plumbing, not to establish statistical performance. The synthetic one-epoch training smoke test creates a disposable model outside this distribution and is not a model-quality experiment.

The original PlantVillage corpus has more crops/classes than this particular model. It contains selected visible conditions, not every possible disease, nutrient deficiency, pest, root problem or growth-stage issue. Tomato spider-mite damage is a pest-damage class, not a disease pathogen classification.

Known failure modes include unfamiliar crops, background shortcuts, poor framing, lighting changes, multiple leaves, simultaneous conditions, visually similar pathogens and disease before visible symptoms. Averaging views is a heuristic; disagreement triggers abstention. Softmax values rank known classes and do not guarantee diagnosis correctness. The model cannot infer yield loss, severity, food safety, exact cultivar or a pesticide prescription.

Included ONNX files are pinned by SHA-256. `restore_starter_model.py` fetches only the pinned files and verifies their expected hashes. It does not run upstream Python code or load an arbitrary pickle checkpoint.
