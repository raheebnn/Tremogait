# Contributing to TremoGait

Contributions are welcome — bug fixes, better features, new datasets, or a proper dashboard app.

## Reporting issues

Include the component (firmware / gait server / tremor script / notebooks), your hardware, OS and Python version, and the console output.

## Pull requests

1. Fork and branch from `main`.
2. Keep each PR focused on one change.
3. Make sure `python -m compileall raspberry_pi dashboard` passes and the sketches still compile.
4. **Never commit** Wi-Fi credentials, API keys, trained models or datasets.
5. **Never commit data from real people** unless you have their consent and it is fully anonymised.
6. Update the README or `docs/` if endpoints, thresholds or wiring change.

## Medical note

This is a screening prototype, not a medical device. Please don't add wording that presents its output as a diagnosis.

By contributing you agree your work is released under the MIT License.
