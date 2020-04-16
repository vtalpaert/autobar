# Autobar

A mechanical cocktail artist built with pumps inside an old coffee machine.

![latest pic for now](media/docs/testing_electronics.jpg)

## Hardware

### Pumps

The pumps are diaphragm pumps, which can lift both air and liquid. We fitted 10 of them inside an unsued coffee machine, each pump costs about 3,50€.

The characteristics are 4W with 12V and less than 300 mA. It theoretically outputs 800 ml / min ± 100 ml. It can push up to 1,5m and pull from 1m, so typically from a bottle on the ground (in a cooler) while the machine is on a table.

![pump showcase](media/docs/motor_fitted.jpg)

In my first version, I used aquarium pumps which cannot lift air. The problem was that I needed to suck the air out of the tubes, plus carbonated drinks made bubbles inside the pump which broke the pump's ability to lift liquid. Furthermore the flow was too important, which prohibits fine volume measuring.

The pumps are controlled from the Raspberry Pi's GPIO by thyristors. They work as controlled switches by connecting the gate to the GPIO without forgetting a pull-down 10kOhm resistor.

### Weight sensing

We use a weight module typically used with Arduinos to sense how much liquid is poured. The HX711 analog to digital amplifier did not work with the `gpiozero` library, so I kept the classic `RPi.GPIO` with code from [here](https://circuitdigest.com/microcontroller-projects/arduino-weight-measurement-using-load-cell/)

### Display and control

Touch screen and reusing the two original buttons. (more explanations to come)

## Software

A Raspberry Pi runs a django server. I wanted a potentially complex database of cocktails, with tables such as Ingredients, Doses, history of Orders, etc. I display my website on the touchscreen, but you could use your smartphone to control your own barmachine. The main point is to use another device to configure the database, especially what is inside the Dispensers.

For a smooth experience, I recommend using a Rapsberry Pi 3 at least. I encountered a lot of WiFi 2.4GHz issues with my Pi 2. The Pi Zero is not suited to use with a touchscreen/desktop.

This is what the website looks like for now :

![intro demo](media/docs/intro.png)
![modal demo](media/docs/modal.png)

The database comes from an open source project (I lost the link, I'll find it again later). I ran into the issue of having way too many ingredients in the scraped DB, so I suggest combining several ingredients into one (like all the Schnapps, sorry).

### Setup

I used this to install a virtual keyboard for the touchscreen :

```bash
sudo apt install at-spi2-core florence
```

I added to the boot options

```bash
#LCD Display HDMI Touchscreen Waveshare

max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 1024 600 60 6 0 0 0
hdmi_drive=1

display_rotate=1 #1: 90; 2: 180; 3: 270
```

And I rotated the touchscreen (see more [here](https://www.waveshare.com/wiki/Template:10.1inch_HDMI_LCD_(B)_Manual))

Use Python 3.5+ and install the dependencies from `requirements.txt`

### TODO

- combine doses of same ingredient (look out for number field)
- no 0.0 quantity for regular ingredients
- eliminate pictures not in DB
- add fixtures with verified mixes
- manually add all mixes with most common alcohol
- set volume to shot (big, small...)
- script to verify mix with online info

## Quick run

```bash
python3 manage.py runserver 0.0.0.0:8000
```

Yes that's Django in debug mode. Not safe to open anywhere else than your local network

## Auto run

We need to start the server and open from a browser on startup.

```bash
crontab -e
```

Then add

```bash
@reboot sleep 10 && /home/pi/autobar/start.sh &
```
