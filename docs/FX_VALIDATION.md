# Gesture Controls Lab v0.2.0 validation — 2 October 2026

## Maintainer Mac

The release candidate was exercised on an Apple-Silicon Mac with:

- CPython 3.12.14
- MediaPipe 1.0.0
- OpenCV contrib 4.13.0
- NumPy 2.3.5
- one OpenCV provider only

`pip check` completed successfully.

The pre-release source suite contained 45 tests. Version 0.2.0 adds one
release-version identity regression, bringing the release-candidate suite to 46.

## Gesture model

`app.py model` downloaded the configured Google gesture-recognizer task bundle
from `storage.googleapis.com`.

Observed local receipt:

- bytes: 8,373,440
- SHA-256: `97952348cf6a6a4915c2ea1496b4b37ebabc50cbbf80571435643c455f2b0482`

This hash records the bytes received from that URL. It is local integrity evidence,
not an independently published upstream signature.

## Native startup

The MediaPipe GestureRecognizer successfully:

- initialized in IMAGE mode,
- performed blank-image inference,
- initialized in VIDEO mode,
- performed blank-frame video inference,
- and closed successfully.

No real-hand recognition accuracy percentage is inferred from those checks.

## Camera boundary

A separate physical-camera smoke test opened local camera index 0 and returned
60 usable frames from 60 read attempts.

This establishes camera acquisition only. It does not validate real gesture-
recognition accuracy, calibration quality, GUI interaction, two-hand tracking
quality, or neon-effect aesthetics.

## Deterministic coverage

The tests exercise model-receipt guards, redirect restrictions, pinch calibration,
temporal gates, independent hand state, ambiguity handling, stale-state cancellation,
bounded visual effects, rendering input preservation, calibration suppression,
worker cleanup, no-backlog behavior, network-camera refusal, and release-version
identity.

Hosted release CI must pass before publication.

No medical, biometric identity, accessibility, safety, or operating-system control
claim is made.
