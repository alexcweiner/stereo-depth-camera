# Contributing

Issues and PRs welcome.

## Dev loop

```sh
uv sync --extra bridge
uv run python -m unittest discover -s tests -v
```

Keep changes focused: one camera, WebRTC ingress, software stereo into Viam.
Multi-module ring / calibration fusion belong in a separate project unless
they stay optional and out of the default path.

## Style

- Prefer small, readable modules over clever abstractions.
- Do not commit `local/viam.json` or other machine credentials.
- Update README examples when you change config attribute names.
