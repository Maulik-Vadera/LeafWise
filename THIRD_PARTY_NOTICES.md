# Third-party notices

## Included pretrained model

- Repository: https://huggingface.co/imaflower/plantvillage-mobilenetv3
- Publisher identifier: imaflower
- Revision: d76fe187be1c4c3a5474f835a7a70cd08c7ab085
- Repository metadata declares: MIT
- Included upstream files: `model.onnx`, `model.onnx.data`, `class_names.json`, `training_config.json`
- Exact hashes for inference weights are recorded in `models/manifest.json`.
- The included weights were trained by the upstream publisher, not by the Leafwise application author.

The upstream model refers to PlantVillage-derived training data. Upstream data rights and documentation should be reviewed before redistributing a dataset or making commercial claims. The original dataset's paper is Mohanty, Hughes & Salathé, “Using Deep Learning for Image-Based Plant Disease Detection,” Frontiers in Plant Science (2016), DOI: 10.3389/fpls.2016.01419.

## MIT license text for model files declared MIT by upstream

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

## Other components

FastAPI, Starlette, Uvicorn, Pillow, NumPy, ONNX Runtime, HTTPX, python-dotenv and python-multipart are installed from their respective distributions. Their own copyright and license notices remain in those packages. Training additionally uses PyTorch, Torchvision and ONNX. Their packages are not vendored inside this ZIP.

Pl@ntNet is an optional external service with its own account, quota, privacy and use terms. No provider model weights or reference photographs are redistributed here. Care-source text has been summarized in original wording; their linked publications retain their respective rights.

The botanical SVG, app icon, interface, application code, tests and project documentation were created for this package. No stock photography or commercial template was used. Raw PlantVillage test/training photos used during checks are not bundled.
