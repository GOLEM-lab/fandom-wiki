import selenium.webdriver as sel
import sys

line = sys.stdin.read().strip()
ffox_web = sel.Firefox()
ffox_web.get(line)

sys.stdout.write(ffox_web.page_source)