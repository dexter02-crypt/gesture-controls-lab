# Gesture Controls Lab v0.2.0

Gesture Controls Lab combines MediaPipe's pretrained gesture categories with
separate session-calibrated pinch controls and bounded neon visual effects.

## Highlights

- Seven pretrained MediaPipe gesture categories.
- Independent 2-D pinch detection and session calibration.
- Pinch counter, in-app drawing, and in-app slider modes.
- Pinch-triggered particles, trails, rings, and a two-hand visual bridge.
- Bounded one-inference worker with stale-result cancellation.
- No operating-system mouse or keyboard control.
- No automatic recording or camera upload.

## Verified local runtime

The maintainer Apple-Silicon Mac used:

- CPython 3.12.14
- MediaPipe 1.0.0
- OpenCV contrib 4.13.0
- NumPy 2.3.5

Native IMAGE and VIDEO GestureRecognizer initialization and blank inference passed.

The configured model download produced a local receipt for 8,373,440 bytes with
SHA-256:

`97952348cf6a6a4915c2ea1496b4b37ebabc50cbbf80571435643c455f2b0482`

That hash is local integrity evidence, not an upstream signature.

A bounded physical-camera smoke check returned 60 usable frames from camera index 0.

## Scope

Synthetic and blank-input tests do not establish real-world gesture-recognition
accuracy.

The two-hand bridge and neon effects are visual decorations, not depth, contact,
identity, or physical measurements.
