# Research and implementation choices

Reviewed on 26 September 2026. These are primary sources: original research, dataset/model maintainers, API owners and extension institutions. The care cards contain short original summaries; follow the linked references for their full context.

| Source | What it informed |
|---|---|
| [Mohanty, Hughes & Salathé (2016)](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2016.01419/full) | Image-based disease classification is feasible, but performance on curated images does not establish performance on different image distributions. |
| [Original PlantVillage repository](https://github.com/spMohanty/PlantVillage-Dataset) | Dataset scope, canonical crop/condition labels and physical-leaf grouping metadata. |
| [Noyan (2022), Uncovering bias in PlantVillage](https://arxiv.org/abs/2206.04374) | Evidence that background information can correlate with class labels; motivates field testing and careful data splits. |
| [Included pretrained model](https://huggingface.co/imaflower/plantvillage-mobilenetv3) | The actual 15-class weights, metadata, training configuration and MIT declaration. |
| [Alternative 38-class MobileNetV2 model](https://huggingface.co/onnx-community/mobilenet_v2_1.0_224-plant-disease-identification-ONNX) | Considered during research; its card declares `license: other`, so its weights were not bundled. |
| [Torchvision MobileNetV3](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.mobilenet_v3_small.html) | Backbone construction and ImageNet preprocessing for the new training workflow. |
| [PyTorch ONNX export](https://docs.pytorch.org/docs/stable/onnx.html) | Export path and numerical comparison with the runtime model. |
| [Pl@ntNet species documentation](https://my.plantnet.org/doc/api/identify) | Repeated image/organ fields, taxonomic response structure and one-individual-per-request behavior. |
| [Pl@ntNet variety documentation](https://my.plantnet.org/doc/api/varieties) | Separate variety endpoint, nested variety candidates and limited coverage. |
| [Pl@ntNet FAQ](https://my.plantnet.org/doc/getting-started/faq) | Additional views of the same individual can improve identification. |
| [UMN tomato leaf spots](https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/yard-and-garden-problems/tomato-leaf-spot-diseases) | Similar-looking symptoms and the value of cultural management/confirmation. |
| [Maryland early blight](https://www.extension.umd.edu/resource/early-blight-tomatoes) | Short tomato early-blight observation and first-step notes. |
| [UMN late blight](https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/late-blight) | Prompt assessment for spreading late-blight-like symptoms. |
| [UMN bacterial spot](https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/bacterial-spot-of-tomato-and-pepper) | Tomato/pepper spotting and non-chemical precautions. |
| [UMN leaf mold](https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/tomato-leaf-mold) | Humidity and checking corresponding leaf surfaces. |
| [Maryland Septoria](https://www.extension.umd.edu/resource/septoria-leaf-spot-tomatoes) | Observational distinctions and splash reduction. |
| [UMN spider mites](https://extension.umn.edu/garden-and-home/yard-and-garden/yard-and-garden-insects/spider-mites) | Stippling, webbing and direct inspection before management decisions. |
| [UMN tomato viruses](https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/tomato-viruses) | Virus-like patterns, handling hygiene and the need for confirmation. |
| [UC IPM yellow leaf curl](https://ipm.ucanr.edu/agriculture/tomato/tomato-yellow-leaf-curl/) | Curling/stunting observations and vector-aware expert follow-up. |
| [ICAR KVKs](https://www.icar.gov.in/en/krishi-vigyan-kendras-kvks) | India-specific referral path to district extension support. |

## Design conclusions

1. A narrower runnable model with a stated scope is more useful than a claim to recognize every tree and disease.
2. Species identity, cultivar identity and disease screening need different evidence and model coverage.
3. Confidence should help decide whether to gather more evidence; a large number must not imply certainty.
4. Treatment text should be traceable and reviewed. The app uses non-chemical first steps and referral guidance, not invented chemical prescriptions.
5. A useful project evaluation should include independent local field data, background variation, unsupported crops, non-leaf objects, and explicit error analysis.

These conclusions are engineering choices informed by the sources, not claims that this implementation has already demonstrated farm-level impact.
