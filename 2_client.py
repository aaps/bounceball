import os
from legume import *

from subprocess import Popen

c1 = Popen(["python", os.path.dirname(__file__)+"/"+"client.py","jimmy1"])
c2 = Popen(["python", os.path.dirname(__file__)+"/"+"client.py","jimmy2"])

c1.wait()
c2.kill()