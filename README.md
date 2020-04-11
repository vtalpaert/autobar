# Autobar

## Setup

Project for python3.5

### Configure Pi

```bash
#LCD Display HDMI Touchscreen Waveshare

max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 1024 600 60 6 0 0 0
hdmi_drive=1

display_rotate=1 #1: 90; 2: 180; 3: 270
```

### Keyboard

```bash
sudo apt install at-spi2-core florence
```

## Sanity check

- combine doses of same ingredient (look out for number field)
- no 0.0 quantity for regular ingredients
- eliminate pictures not in DB
- add fixtures with verified mixes
- manually add all mixes with most common alcohol
- set volume to shot (big, small...)
- script to verify mix with online info

## References

- [Weight module](https://circuitdigest.com/microcontroller-projects/arduino-weight-measurement-using-load-cell/)

## Quick run

xvfb-run -s "-screen 0 1400x900x24" bash
python manage.py runserver 0.0.0.0:8000

