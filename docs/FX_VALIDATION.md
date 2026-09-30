# FX revision validation

Historical 0.1.0 test records remain intact and describe their original build.
This revision adds native OpenCV processing and regression checks plus mocked
camera/gesture events where necessary. See the final FX pack's validation reports
for exact fresh-extracted executions. ZXing 3.1.1 and the trained gesture model
were reported running in the owner's supplied Mac log, but could not be freshly
acquired/executed in this Linux build. That distinction is preserved.

Camera-frame effects are rendered on a copy, after inference; turning on neon
cannot improve recognition accuracy. No physical camera or remote CI pass is claimed.
