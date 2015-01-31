import os
from legume import *

from subprocess import Popen

s1 = Popen(["python", os.path.dirname(__file__)+"/"+"server.py"])
c1 = Popen(["python", os.path.dirname(__file__)+"/"+"client.py","jimmy1"])
c2 = Popen(["python", os.path.dirname(__file__)+"/"+"client.py","jimmy2"])

c1.wait()
c2.kill()
s1.kill()