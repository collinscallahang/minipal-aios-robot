# MiniPal SolidWorks Finished Model

## Open This First

- Finished robot model: `finished/MiniPal_finished_robot.SLDPRT`
- Source visual part: `parts/MiniPal_simulation_style_robot.SLDPRT`
- Automation script: `../scripts/build_minipal_solidworks.py`

## What It Looks Like

The finished model is a single integrated robot that follows the browser
simulator appearance instead of the exploded internal-layout view:

- separate head, neck, and body
- HC-SR04 double ultrasonic eyes
- face slot below the eyes
- LED ring on the body
- ESP32 state/display window
- speaker grille
- top wake button

## Notes

The `parts/` folder also keeps simplified size-reference parts for ESP32,
HC-SR04, SG90, WS2812, buzzer, battery, case, and wiring. Those are supporting
layout references only. The file to view as the final product is:

`finished/MiniPal_finished_robot.SLDPRT`

## Reference Dimensions

- Project case reference: `100 x 90 x 70 mm`
- HC-SR04 reference envelope: `45 x 20 x 15 mm`
- SG90 reference envelope: `22.2 x 11.8 x 31 mm`
- ESP32 DevKit reference envelope: about `55 x 28 mm`

