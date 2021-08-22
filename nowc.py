#!/usr/bin/python3
# coding:utf-8

from PIL import Image, ImageDraw
from datetime import datetime
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
import base64
import glob
import math
import multiprocessing
import os
import sys
import time
import unicornhat as unicorn


# pixel (60pixel = 500m)
area_size = 2 * 60
browser_name = 'chrome'
cnt = 0
image_ext = 'png'
lat = 35.681236
lon = 139.76712
nowcast_url = 'https://www.jma.go.jp/bosai/nowc/#zoom:14/lat:%f/lon:%f/colordepth:deep/elements:hrpns'
kotan_url = 'https://www.jma.go.jp/bosai/kaikotan/#lat:%f/lon:%f/zoom:14/colordepth:deep/elements:rasrf'
window_size = 800

try:
    if len(sys.argv) == 3:
        lat = float(sys.argv[1])
        lon = float(sys.argv[2])
except:
    print('sys.arg', 'except')

notes = {
    '80': (180, 0, 104, 255),
    '50': (255, 40, 0, 255),
    '30': (255, 153, 0, 255),
    '20': (250, 245, 0, 255),
    '10': (0, 65, 255, 255),
    '5': (33, 140, 255, 255),
    '1': (160, 210, 255, 255),
    '0': (242, 242, 255, 255),
    '-': (0, 0, 0, 255)
}


def driver_preparation(browser_name, debug_mode):
    options = Options()
    options.binary_location = '/usr/bin/chromium-browser'
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("disable-infobars")
    options.add_argument("start-maximized")
    options.add_argument('--headless')
    options.use_chromium = True
    driver = webdriver.Chrome(options=options, executable_path='/usr/bin/chromedriver')
    return driver


def clear_ad(wait):
    ad_block_button = wait.until(expected_conditions.visibility_of_element_located((By.CLASS_NAME, 'jmatile-clear-ad')))
    ad_block_button.click()


def get_image_filename(wait, mode):
    map_title = wait.until(
        expected_conditions.visibility_of_element_located((By.CLASS_NAME, 'jmatile-map-title-validtime')))
    image_title = map_title.text.replace('\u307e\u3067', '')
    imagename = datetime.strptime(image_title, '%Y\u5e74%m\u6708%d\u65e5%H\u6642%M\u5206').strftime('%Y%m%d%H%M00')
    filename = '%s_%f_%f_%s.%s' % (mode, lat, lon, image_title, image_ext)
    return (imagename, filename)


def get_key(d, val):
    keys = [k for k, v in d.items() if v == val]
    if keys:
        return keys[0]
    return '-1'


def get_forecasts(imagename, filename, map_image, debug_mode):
    im = Image.open(BytesIO(map_image))
    center_x, center_y = math.ceil(im.size[0] / 2) - 1, math.ceil(im.size[1] / 2) - 1
    max_rain = '-1'
    for y in range(center_y - area_size, center_y + area_size):
        for x in range(center_x - area_size, center_x + area_size):
            rgba = im.getpixel((x, y))
            rain = get_key(notes, rgba)
            if int(max_rain) < int(rain):
                max_rain = rain

    return {imagename: max_rain.replace('-1', '-')}


def progress():
    global cnt
    unicorn.clear()
    if cnt % 4 == 0:
        unicorn.set_pixel(3,3,0,255,255)
    if cnt % 4 == 1:
        unicorn.set_pixel(3,4,0,255,255)
    if cnt % 4 == 2:
        unicorn.set_pixel(4,4,0,255,255)
    if cnt % 4 == 3:
        unicorn.set_pixel(4,3,0,255,255)
    unicorn.show()
    time.sleep(0.1)
    cnt = cnt + 1


def access_nowcast(driver, lat, lon, page, mode, debug_mode):
    driver.set_window_size(window_size, window_size)
    if mode == 'kotan':
        driver.get(kotan_url % (lat, lon))
    else:
        driver.get(nowcast_url % (lat, lon))
    wait = WebDriverWait(driver, 15)
    time.sleep(1)
    try:
        clear_ad(wait)
    except:
        pass

    forecasts = []
    for i in range(page):
        progress()
        time.sleep(1)

        imagename, filename = get_image_filename(wait, mode)

        map_image = driver.find_element_by_class_name('jmatile-map').screenshot_as_png
        forecast = get_forecasts(imagename, filename, map_image, debug_mode)
        forecasts.append(forecast)

        try:
            driver.find_elements_by_css_selector('[id^=jmatile_time_next_')[0].click()
        except Exception as e:
            break

    return forecasts


def main(lat, lon, page, mode, debug_mode):
    driver = driver_preparation(browser_name, debug_mode)
    try:
        result = {'location': {'lat': lat, 'lon': lon}}
        forecasts = access_nowcast(driver, lat, lon, page, mode, debug_mode)
        result.update({'forecasts': forecasts})
        return result
    finally:
        driver.close()


def progress_worker():
    for n in range(300 * 2):
        progress()


if __name__ == '__main__':
    unicorn.set_layout(unicorn.AUTO)
    unicorn.rotation(0)
    unicorn.brightness(0.5)
    width,height=unicorn.get_shape()
    unicorn.clear()

    progress_process = multiprocessing.Process(name="progress_process", target=progress_worker)
    progress_process.start()

    result1 = main(lat, lon, 13, 'nowc', False)
    result2 = main(lat, lon, 16, 'kotan', False)

    progress_process.terminate()
    unicorn.clear()

    # now
    r, g, b, _ = notes[list(result1['forecasts'][0].values())[0]]
    unicorn.set_pixel(0,0,r,g,b)

    for i in range(1, 7):
        r, g, b, _ = notes[list(result1['forecasts'][i].values())[0]]
        unicorn.set_pixel(1+i,0,r,g,b)

    for i in range(7, len(result1['forecasts'])):
        r, g, b, _ = notes[list(result1['forecasts'][i].values())[0]]
        unicorn.set_pixel(i-5,1,r,g,b)

    # now
    r, g, b, _ = notes[list(result2['forecasts'][0].values())[0]]
    unicorn.set_pixel(0,2,r,g,b)

    for i in range(1, 7):
        r, g, b, _ = notes[list(result2['forecasts'][i].values())[0]]
        unicorn.set_pixel(1+i,2,r,g,b)

    for i in range(7, 13):
        r, g, b, _ = notes[list(result2['forecasts'][i].values())[0]]
        unicorn.set_pixel(i-5,3,r,g,b)

    for i in range(13, len(result2['forecasts'])):
        r, g, b, _ = notes[list(result2['forecasts'][i].values())[0]]
        unicorn.set_pixel(i-11,4,r,g,b)

    unicorn.show()
    time.sleep(240)
