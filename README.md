# Gesture Controls Lab — Neon FX

Trained MediaPipe gesture categories plus independent calibrated pinch controls.
The FX revision adds pinch-triggered bursts, coloured fingertip trails, orbiting
rings and a light bridge when two tracked hands are actively pinching.

![Synthetic interaction-event rendering](docs/fx-demo.png)

## Run

Use the existing working Python 3.12 / MediaPipe 1.0.0 environment. Do not upgrade
it as part of this source-only FX change. The surrounding Next Lab launcher still
works; the FX pack provides `python3 studio.py run gestures --max-hands 2`.
For an independent clone, install requirements in an isolated Python 3.12 .venv,
run `app.py model`, `app.py check`, then `app.py camera`.

O samples naturally separated thumb/index fingers for two seconds; P samples a
natural pinch for two seconds. Use one complete hand during calibration. Reopen
fingers before using the controls. Calibration is session-only.

1 selects pinch counting, 2 drawing and 3 an in-app slider. E switches neon effects
on/off. R resets the session, C clears strokes, Q/Esc exits. There is no system
mouse/keyboard control, video recording or camera upload by application code.

The effects respond to accepted interaction events, not every repeated video
frame. Effects are bounded and cleared on resets, stale input and calibration.
The two-hand bridge is a visual decoration, not contact or depth measurement.

## Limits

The seven trained categories, landmark model, association logic, pinch thresholds
and temporal decision rules are unchanged by FX. The build adds no new gesture
recognition accuracy claim. Tracking can fail on occlusion, small hands, crossings
or slow observations. A reported local native startup pass is not a camera benchmark.

Application source: MIT. Preserve THIRD_PARTY.md, including MediaPipe/model notices.
See docs/FX_VALIDATION.md for exactly which checks ran in the FX build.
