file = open("config.txt","r")
for line in file.readlines():
    line = line.strip()
    if line.startswith("#"): continue
    if line == "": continue
    try:
        line = line.split("=")
        line = [x.strip(" ") for x in line]
        if line[0] == "ip": HOST = line[1][1:-1]
        elif line[0] == "port": PORT = int(line[1])
        elif line[0] == "music": MUSIC = int(line[1])
        elif line[0] == "sfx": SFX = int(line[1])
        elif line[0] == "player_name": PLAYER_NAME = line[1][1:-1]
    except:
        print("Invalid line: \""+line+"\"!")
file.close()