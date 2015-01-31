import threading
import time
import legume
import shared
import pygame
import sys
import random
import pickle
import math
import itertools

DUMP_DEBUG_LOG = 0
PRINT_DEBUG_HUD = 0

HOST = 'localhost'


MOVE_FEEDBACK = 0

fullscreen =  0#pygame.FULLSCREEN
MUSIC = 0
SFX = 1
PLAYER_NAME = "jimdmsy2"

DATADIR = "data"
#font
FONTDIR = "data"
FONTS = [('prstartk',10),('prstartk',40),('prstartk',20)]

from config_txt import *

#color
_NUMERALS = '0123456789abcdefABCDEF'
_HEXDEC = {v: int(v, 16) for v in (x+y for x in _NUMERALS for y in _NUMERALS)}
LOWERCASE, UPPERCASE = 'x', 'X'
def hexToRgb(triplet): return (_HEXDEC[triplet[0:2]], _HEXDEC[triplet[2:4]], _HEXDEC[triplet[4:6]])
colors = ['ff0000','00ff00','0000ff','ffff00','ff00fe','00ffff','880000','008800','000088','888800','880088','008888','ff8888','88ff88','8888ff','888888']


class GameClient(object):
    def __init__(self):
        self.running = 1
        self.world = shared.World(0)
        self._client = legume.Client()
        self._client.OnMessage += self.on_message        
        self.force_sync = 1
        self.log = {}
        self.client_entity_count = 0
        self.client_focus = (1,1)

        #client logic
        self.logic_timer = time.time()
        self.move_timer = time.time()
        self.fire_timer = time.time()

        self.font = None
        self.image = None
        self.image_tile = None
        if len(sys.argv) > 1: self.player_name = sys.argv[1]
        else: self.player_name = PLAYER_NAME
        self.camera_x = -1
        self.camera_y = -1
        self.surface = None
        self.fps = (time.time(),0,0)
        self.tiles_string_client = ''

    def on_message(self, sender, msg):
        if DUMP_DEBUG_LOG: self.log[msg.message_id] = msg
        if legume.messages.message_factory.is_a(msg, 'PlayerUpdate'): self.message_player(msg)
        elif legume.messages.message_factory.is_a(msg, 'AvatarUpdate'): self.avatar_message(msg)
        elif legume.messages.message_factory.is_a(msg, 'EntityUpdate'): self.entity_message(msg)
        elif legume.messages.message_factory.is_a(msg, 'WorldUpdate'): self.world_message(msg)
        elif legume.messages.message_factory.is_a(msg, 'LevelUpdate'): self.level_message(msg)
        else:
            raise KeyError() #add message typr!
            #print('Message: %s' % args)

    def connect(self, host='localhost'):
        if self._client._state not in [self._client.CONNECTED, self._client.CONNECTING]:
            print('Using host/port: %s %s' % (host, shared.PORT))
            self._client.connect((host, shared.PORT))
        
    #response
    def message_player(self, msg):
        print('Got status for player %s' % msg.player_id.value)
        if msg.player_id.value not in self.world.player:
            print('Update player')
            e = shared.Player()
            e.message(msg)
            self.world.world_insert_player(e)
        else:
            self.world.player[msg.player_id.value].message(msg,False)

    def avatar_message(self, msg):
        if self.world.player.get(msg.player_id.value) is None:
            #create temp player and assign id
            e = shared.Player()
            e.player_id = msg.player_id.value
            self.world.world_insert_player(e)
        
        self.entity_message(msg)
        self.world.entity[msg.entity_id.value].player_id = msg.player_id.value
        self.world.player[msg.player_id.value].entity_id = msg.entity_id.value

    def entity_message(self, msg):
        print('Got status for entity %s' % msg.entity_id.value)        
        if msg.entity_id.value not in self.world.entity:
            print('Creating new entity')
            e = shared.Entity()            
            e.message(msg)
            self.world.world_insert_entity(e)
            self.play_sound(msg.key.value, e, 'spawn')
        else:
            e = self.world.entity[msg.entity_id.value]            
            spawned = 0 if e.entity_spawn_id == msg.entity_spawn_id.value else 1
            self.world.entity[msg.entity_id.value].message(msg,False)
            if spawned: self.play_sound(msg.key.value, e, 'spawn')

        

    def play_sound(self, key, e1, event):
        if not SFX: return
       
        x=(self.camera_x- e1.x/shared.ZONE_SCALE)
        y=(self.camera_y- e1.y/shared.ZONE_SCALE)
        sound_dist = 600.0
        dist_vol = (sound_dist-min(math.sqrt(x**2+y**2),sound_dist)) /sound_dist
        if dist_vol > 0.02:
            v = min(dist_vol*1.3,1.0)
            vl = v*math.fabs(((self.camera_x + shared.ZONE_SCREEN_WIDTH/3) - e1.x/shared.ZONE_SCALE)/sound_dist)
            vr = v*math.fabs(((self.camera_x - shared.ZONE_SCREEN_WIDTH/3) - e1.x/shared.ZONE_SCALE)/sound_dist)
            if key == shared.KEY_SHOT_A:
                if event == 'spawn':
                    try:
                        channel = self.sound['fire1'].play()
                        channel.set_volume(vl,vr)
                    except: pass
                elif event == 'bounce':
                    try:
                        channel = self.sound['fire_bounce0'].play()
                        channel.set_volume(vl,vr)
                    except: pass
            elif key == shared.KEY_POWERUP_A:
                if event == 'pick':
                    try:
                        channel = self.sound['powera0'].play()
                        channel.set_volume(vl,vr)
                    except: pass

    def world_message(self, msg):
        print('Got status for world %s' % msg.frame_number.value)
        self.world._world_frame_number = msg.frame_number.value

    def level_message(self, msg):
        print('Got status for level')
        self.world.build_level(msg.tiles.value)        
        
    #command player
    def my_player_name(self):
        name = self.player_name
        name = name[:32] #limit 32
        name = name.encode('ascii','ignore')
        return name

    def my_player_id(self):
        name = self.my_player_name()
        player_id = shared.hashed_int_mod(name+str(shared.mac),65536)
        return player_id

    def my_player_color(self):
        name = self.my_player_name()
        return shared.hashed_int_mod(name+str(shared.mac),len(colors)) 

    def my_player(self):
        return self.world.player.get(self.my_player_id())

    def my_avatar(self):
        p = self.my_player()
        if p is None: return None
        return self.world.entity.get(p.entity_id)

    def force_resync(self, endpoint):
        msg = shared.ResyncCommand()
        try:
            endpoint.send_reliable_message(msg) #fix: check connectivity
            self.force_sync = 0
        except:
            pass 

    #client only command 
    def client_only_message(self, msg):
        if msg.MessageTypeID == shared.ClientSpawnEntityCommand.MessageTypeID: #
            e = shared.Entity()
            self.client_entity_count += 1
            e.entity_id = self.client_entity_count
            e.key = msg.key
            if e.key == shared.KEY_MOVE:
                e.release = self.world._world_frame_number + 20
            e.x = msg.x
            e.y = msg.y
            e.vx = msg.vx
            e.vy = msg.vy
            self.world.world_insert_client_entity(e)

    def spawn_client_entity(self, key, position):
        print('spawn_client_entity')
        msg = shared.ClientSpawnEntityCommand()
        msg.key = key
        msg.x = position[0]
        msg.y = position[1]
        try:
            self.client_only_message(msg) #fix: check connectivity
        except:
            pass 


    #command player
    def spawn_player(self, endpoint):
        print('spawn_player')
        name = self.my_player_name()
        player_id = self.my_player_id()
        player_color = self.my_player_color()

        msg = shared.CreatePlayerCommand()
        msg.player_id.value = player_id
        msg.player_color.value = player_color
        msg.name.value = name

        try:
            endpoint.send_reliable_message(msg) #fix: check connectivity
        except:
            pass 

    
    def spawn_entity2(self, endpoint, entity_id, key, position, target_position): #target
        print('spawn_entity2')
        msg = shared.CreateEntity2Command()
        msg.entity_id.value = entity_id
        msg.key.value = key #type of entity
        msg.x.value = position[0]
        msg.y.value = position[1]
        msg.tx.value = target_position[0]
        msg.ty.value = target_position[1]
        try:
            endpoint.send_reliable_message(msg) #fix: check connectivity
        except:
            pass

    def spawn_avatar(self, endpoint, player_id, position, key):
        print('spawn_avatar')
        msg = shared.CreateAvatarCommand()
        msg.player_id.value = player_id
        msg.key.value = key
        msg.x.value = position[0]
        msg.y.value = position[1]
        try: endpoint.send_reliable_message(msg) #fix: check connectivity
        except: pass 

    def move_entity4(self, endpoint, entity_id, pos):
        print('move_entity4')
        msg = shared.MoveEntity4Command()
        msg.entity_id.value = entity_id
        msg.tx.value = pos[0]
        msg.ty.value = pos[1]
        msg.client_frame.value = self.world._world_frame_number
        try: endpoint.send_message(msg) #fix: check connectivity
        except: pass 

    def spawn_level(self, endpoint, tiles):
        print('spawn_level')
        msg = shared.CreateLevelCommand()
        msg.tiles.value = tiles
        try: endpoint.send_reliable_message(msg) #fix: check connectivity
        except: pass




    def act(self,mode,key,vec=None):
        win = self.world.get_winner()
        if len(win) > 0: 
            t = self.world.get_time_to_next_game(win)
            if t == 5:
                for e in self.world.entity.itervalues():
                    e.reset()
            return

        e = self.my_avatar()
        if e is None: return        
        if e.release > 0 and self.world._world_frame_number >= e.release: return

        if vec is not None:            
            x2,y2 = vec
            x = e.x + x2*shared.ZONE_SCALE
            y = e.y + y2*shared.ZONE_SCALE
        else:
            x,y = pygame.mouse.get_pos()
            x += self.camera_x
            y += self.camera_y
            x -= shared.ZONE_SCREEN_WIDTH/2
            y -= shared.ZONE_SCREEN_HEIGHT/2
            x *= shared.ZONE_SCALE
            y *= shared.ZONE_SCALE
        
        if mode == 'move':
            if time.time() > self.move_timer + 0.2: #5 per second
                self.move_timer = time.time()

                self.move_entity4(self._client, e.entity_id, (x, y))
                if MOVE_FEEDBACK: #move feedback
                    self.spawn_client_entity(shared.KEY_MOVE,(x, y))
        if mode == 'fire':
            a = self.my_avatar()
            if a is not None:
                energy_cost = shared.ENERGY_COST_FIRE_SHOT
                if a.energy >= energy_cost:
                    if time.time() > self.fire_timer + shared.COOLDOWN_SHOTA: #shots per second
                        if key == 'shot': 
                            self.fire_timer = time.time()
                            a.energy -= energy_cost
                            key2 = shared.KEY_SHOT_A
                        self.spawn_entity2(self._client, e.entity_id, key2, (e.client_x, e.client_y), (x, y))

    def on_client_entity_collision(self):
        for e in self.world.entity_events:
            if e.key == shared.KEY_SHOT_A:
                self.play_sound(e.key, e, 'bounce')
            elif e.key == shared.KEY_POWERUP_A:
                self.play_sound(e.key, e, 'pick')


    def on_logic(self):
        #print('Logic: %s' % self.logic_timer)
        
        #todo, add command_delay for each command, so every command can have their own cycle

        #client commands
        keys = pygame.key.get_pressed()
        b1,b2,b3 = pygame.mouse.get_pressed()

        if b1: self.act('fire', 'shot')

        v1 = 200
        v2 = 141
        kl,kr,ku,kd=keys[pygame.K_a],keys[pygame.K_d],keys[pygame.K_w],keys[pygame.K_s]
        if kl and not kr:
            if ku and not kd: self.act('move', None, (-v2, -v2))
            if kd and not ku: self.act('move', None, (-v2, v2))
            else: self.act('move', None, (-v1, 0))
        elif kr and not kl:
            if ku and not kd: self.act('move', None, (v2, -v2))
            if kd and not ku: self.act('move', None, (v2, v2))
            else: self.act('move', None, (v1, 0))
        elif ku and not kd: self.act('move', None, (0, -v1))
        elif kd and not ku: self.act('move', None, (0, v1))

        #logic
        if time.time() > self.logic_timer + shared.CLIENT_LOGIC_INTERVAL: #client logic
            self.logic_timer +=  shared.CLIENT_LOGIC_INTERVAL*2
            self.connect(self.host)

            if self.force_sync == 1: #resync if client restarted
                self.force_resync(self._client)

            p = self.world.player.get(self.my_player_id())
            if p is None: self.spawn_player(self._client) #spawn me if i just connected
            elif p.entity_id is 0: #spawn avatar if i just connected
                x = 400# #fix: remove since not used, since player get it by server
                y = 400# #fix: remove since not used, since player get it by server
                self.spawn_avatar(self._client, self.my_player_id(), (x, y), shared.KEY_AVATAR_A)

    def on_key(self, keys, event, mode):
        if   event.key == pygame.K_ESCAPE: 
            if DUMP_DEBUG_LOG:
                fn = 'zz_client_dump'+str(int(time.time()))
                s = str(self.world)
                f = open(fn+'.txt', 'w')
                s = s.replace(', \'', ', \n\'')
                s = s.replace('}, ', '}, \n')
                f.write(s)
                f.close()
                f = open(fn+'_log.txt', 'w')
                s = str(self.log)
                s = s.replace(', \'', ', \n\'')
                s = s.replace('}, ', '}, \n')
                f.write(s)
                f.close()
            self.running = 0
        elif event.key == pygame.K_SPACE:
            self.log.clear()

    def on_mouse(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            b1,b2,b3 = pygame.mouse.get_pressed()
            if b1: pass
            elif b3: pass

    def on_draw(self):
        mx,my = pygame.mouse.get_pos()

        #camera
        mx2 = mx-shared.ZONE_SCREEN_WIDTH /2
        my2 = my-shared.ZONE_SCREEN_HEIGHT /2
        e = self.my_avatar()
        if e is not None:
            self.camera_x = e.x / shared.ZONE_SCALE
            self.camera_y = e.y / shared.ZONE_SCALE
            self.camera_x += mx2/2 #camera between avatar and mouse
            self.camera_y += my2/2
            if int(self.camera_x) < shared.ZONE_SCREEN_WIDTH /2: self.camera_x = shared.ZONE_SCREEN_WIDTH/2
            elif int(self.camera_x) > int(shared.ZONE_WIDTH/shared.ZONE_SCALE) - (shared.ZONE_SCREEN_WIDTH/2) -34: self.camera_x = int(shared.ZONE_WIDTH/shared.ZONE_SCALE) - (shared.ZONE_SCREEN_WIDTH/2) -34
            if int(self.camera_y) < shared.ZONE_SCREEN_HEIGHT /2: self.camera_y = shared.ZONE_SCREEN_HEIGHT/2            
            elif int(self.camera_y) > int(shared.ZONE_HEIGHT/shared.ZONE_SCALE) - (shared.ZONE_SCREEN_HEIGHT/2) -34: self.camera_y = int(shared.ZONE_HEIGHT/shared.ZONE_SCALE) - (shared.ZONE_SCREEN_HEIGHT/2) -34
        if self.camera_x == -1 and self.camera_y == -1: 
            self.surface.fill((0,0,0))

            txt = self.font['prstartk40'].render('BIRDIETRON 24:',True,pygame.Color(random.randint(0,255),random.randint(0,255),random.randint(0,255)))
            txtx,txty = txt.get_size()
            txtx = shared.ZONE_SCREEN_WIDTH/2-txtx/2
            txty = shared.ZONE_SCREEN_HEIGHT/4
            self.surface.blit(txt,(txtx,txty))

            for i, t in enumerate(["Flytta med WASD. Sikta och skjut med med musen.", "Den forste till "+str(shared.GAME_POINTS_TO_WIN) +" score winner.","","Lycka till!"]):
                txt = self.font['prstartk10'].render(t,True,pygame.Color(255,255,255))
                self.surface.blit(txt,(12,i*12))
            pygame.display.flip()
            return

        #level
        gray = (125,125,125)
        black = (0,0,0)
        whitegray = (224,224,224)
        
        tw = (shared.ZONE_SCREEN_WIDTH / shared.TILE_SIZE) + 1 +1
        th = (shared.ZONE_SCREEN_HEIGHT / shared.TILE_SIZE) + 1 +1 
        tx =  int((int(self.camera_x) - (shared.ZONE_SCREEN_WIDTH /2)) / shared.TILE_SIZE)
        ty =  int((int(self.camera_y) - (shared.ZONE_SCREEN_HEIGHT/2)) / shared.TILE_SIZE)
        txm =  int(int(self.camera_x) - (shared.ZONE_SCREEN_WIDTH /2)) % shared.TILE_SIZE
        tym =  int(int(self.camera_y) - (shared.ZONE_SCREEN_HEIGHT/2)) % shared.TILE_SIZE
        py = 0
        for y in range(ty+0, ty+th):
            px = 0
            for x in range(tx+0,tx+tw):
                try:
                    t = self.world.tile[y][x].tile_image
                except: 
                    t = -2 #todo, fix 
                if t == 0: self.surface.fill(gray,(px-txm,py-tym,shared.TILE_SIZE,shared.TILE_SIZE)) #gray floor
                elif t == -1: self.surface.fill(black,(px-txm,py-tym,shared.TILE_SIZE,shared.TILE_SIZE)) #black floor
                elif t == -2: self.surface.fill(whitegray,(px-txm,py-tym,shared.TILE_SIZE,shared.TILE_SIZE)) #white wall
                else:
                    i = self.image_tile[t]
                    self.surface.blit(i,(px-txm,py-tym))
                px += shared.TILE_SIZE
            py += shared.TILE_SIZE


        #entitis
        ents = itertools.chain(self.world.entity.values(), self.world.client_entity.values())
        for e in ents:
            x,y,vx,vy = e.x,e.y,e.vx,e.vy
            x /= shared.ZONE_SCALE
            y /= shared.ZONE_SCALE
            x -= self.camera_x 
            y -= self.camera_y 
            x += shared.ZONE_SCREEN_WIDTH/2
            y += shared.ZONE_SCREEN_HEIGHT/2
            
            if 0: #todo optimize: check if object is outside screen
                continue

            #entity text
            if e.player_id != 0: #player text
                p = self.world.player.get(e.player_id)
                if p is not None and p.entity_id == e.entity_id:
                    txt = self.font['prstartk10'].render(p.name,True,pygame.Color(*hexToRgb(colors[p.player_color])))
                    self.surface.blit(txt,(x-len(p.name)*5,y-44))
            if 0 and e.release > 0: #release text
                txt = self.font['prstartk10'].render(str(self.world._world_frame_number-e.release),True,pygame.Color(255,255,255))
                self.surface.blit(txt,(x-8,y-64))
                #text              
            if e.hp > 0:
                hp = int(int(e.hp)/10)
                sh = int(int(e.shield)/10)
                hpsh = hp+sh
                en = int(int(e.energy)/10)
                for i in range(hpsh):
                    if i < hp: c = (0,200,0)
                    else: c = (200,200,100)
                    self.surface.fill(c,(x+i*4-hpsh*2,y-24-8,2,6)) 
                for i in range(en):
                    c = (250,250,0)
                    self.surface.fill(c,(x+i*4-en*2,y-24,2,4))

            #entity img
            if e.release > 0 and e.release <= self.world._world_frame_number: 
                pass #dont draw cause i am removed
            elif e.key == 0: #default pic
                pass
            elif e.key > 0:
                img = None
                if e.key == shared.KEY_AVATAR_A:
                    idle = e.is_idle()
                    dir = int(vx<0)
                    frm = idle or int(self.world._world_frame_number/20)%2
                    img = self.image['ww'+str(frm)]
                    img = pygame.transform.flip(img,dir,0)
                    x3,y3,imgw,imgh = img.get_rect()
                    self.surface.blit(self.image['shadow0'],(int(x-imgw/2),int(y+imgh/4)))                    
                elif e.key == shared.KEY_MOVE: img = self.image['move']
                elif e.key == shared.KEY_POWERUP_A: img = self.image['powerupa0']
                elif e.key == shared.KEY_SHOT_A:
                    img = self.image['shota']
                    pi = math.pi
                    angle = math.atan2(((e.y+e.vy) - e.y), ((e.x+e.vx) - e.x)) / pi# * 2.0
                    angle *= -180
                    img = pygame.transform.rotate(img, angle)
                if img is not None:
                    x3,y3,imgw,imgh = img.get_rect()
                    self.surface.blit(img,(int(x-imgw/2),int(y-imgh/2)))


        #calc fps
        fps_timer,fps_count,fps = self.fps
        fps_count += 1
        delta = time.time() - fps_timer
        if delta > 1.0:
            fps = fps_count
            fps_timer += 1.0
            fps_count = 0
        self.fps = (fps_timer,fps_count,fps) #set    

        #draw hud
        y_space = 13
        x = shared.ZONE_SCREEN_WIDTH-(9*12)
        i = 0
        txt = self.font['prstartk10'].render('fps:  '+str(fps),True,(200,200,200))
        self.surface.blit(txt,(x,i*y_space))

        i = 1
        txt = self.font['prstartk10'].render('ping: '+str(int(self._client.latency)),True,(200,200,200))
        self.surface.blit(txt,(x,i*y_space))

        if PRINT_DEBUG_HUD:
            i = 2
            txt = self.font['prstartk10'].render('fram: '+str(self.world._world_frame_number),True,(200,200,200))
            self.surface.blit(txt,(x,i*y_space))

            i = 3
            txt = self.font['prstartk10'].render('enti: '+str(len(self.world.entity)),True,(200,200,200))
            self.surface.blit(txt,(x,i*y_space))

            i = 4
            txt = self.font['prstartk10'].render('cent: '+str(len(self.world.client_entity)),True,(200,200,200))
            self.surface.blit(txt,(x,i*y_space))    

            i = 5
            txt = self.font['prstartk10'].render('log: '+str(len(self.log)),True,(200,200,200))
            self.surface.blit(txt,(x,i*y_space))

            i = 6
            txt = self.font['prstartk10'].render('focus: '+str((self.client_focus)),True,(200,200,200))
            self.surface.blit(txt,(-32+x,i*y_space))

        #players
        x = 0
        i = 0
        txt = self.font['prstartk10'].render('player    score/kills/deaths  --- get '+str(shared.GAME_POINTS_TO_WIN)+' score to win ---',True,pygame.Color(255,255,255))
        self.surface.blit(txt,(x,i*y_space))

        i = 1
        p_sorted = sorted(self.world.player.values(), key = lambda p: (p.score, p.kills, p.deaths, p.player_id, p.player_color), reverse = True)
        for p in p_sorted:
            txt = self.font['prstartk10'].render(p.name+': '+str(p.score)+'/'+str(p.kills)+'/'+str(p.deaths),True,pygame.Color(*hexToRgb(colors[p.player_color])))
            self.surface.blit(txt,(x,i*y_space))
            i += 1

        #winner
        winner = self.world.get_winner()
        if len(winner) > 0:
            txt = self.font['prstartk40'].render('WINNER IS:',True,pygame.Color(*hexToRgb(colors[winner[0].player_color])))
            txtx,txty = txt.get_size()
            txtx = shared.ZONE_SCREEN_WIDTH/2-txtx/2
            txty = shared.ZONE_SCREEN_HEIGHT/2-txty
            self.surface.blit(txt,(txtx,txty))
            for i,w in enumerate(winner):
                txt = self.font['prstartk40'].render(w.name,True,pygame.Color(*hexToRgb(colors[w.player_color])))
                self.surface.blit(txt,(txtx,txty+(i+1)*42))

            #next_game_delay = min(0, math.fabs(self.world._world_frame_number - winner[0].winner + shared.PHYSICS_FRAMES_PER_SECOND * shared.WIN_GAME_TEXT_SECONDS))
            next_game_delay = self.world.get_time_to_next_game(winner)
            txt = self.font['prstartk20'].render('Next game starts in: ' + str(next_game_delay),True,pygame.Color(*hexToRgb(colors[winner[0].player_color])))
            txtx,txty = txt.get_size()
            txtx = shared.ZONE_SCREEN_WIDTH/2-txtx/2
            txty = shared.ZONE_SCREEN_HEIGHT-txty-40
            self.surface.blit(txt,(txtx,txty))

        #cursor
        x,y = pygame.mouse.get_pos()
        self.surface.blit(self.image['pointer'], (x,y))
        pygame.display.flip()


    def scale2(self, img):
        sx,sy = img.get_size()
        return pygame.transform.scale(img, (sx*2,sy*2))

    def init_data(self):
        self.surface = pygame.display.set_mode((shared.ZONE_SCREEN_WIDTH,shared.ZONE_SCREEN_HEIGHT),fullscreen)#,pygame.FULLSCREEN)#RESIZABLE)#FULLSCREEN)#RESIZABLE)

        self.font = {fname+str(fsize):pygame.font.Font(FONTDIR+"/"+fname+'.ttf', fsize) for fname,fsize in FONTS}
        self.sound = {}
        self.image = {}
        self.image_tile = []

        self.image['pointer'] = pygame.image.load(DATADIR+'/pointer.png')
        self.image['move'] = pygame.image.load(DATADIR+'/move.png')
        self.image['shota'] = pygame.image.load(DATADIR+'/shota0.png')
        self.image['shadow0'] = pygame.image.load(DATADIR+'/shadow0.png')
        self.image['powerupa0'] = pygame.image.load(DATADIR+'/powerupa0.png')
        self.image['ww0'] = self.scale2(pygame.image.load(DATADIR+'/ww0.png'))
        self.image['ww1'] = self.scale2(pygame.image.load(DATADIR+'/ww1.png'))

        self.image_tile.append(pygame.image.load(DATADIR+'/tile0.png'))
        self.image_tile.append(pygame.image.load(DATADIR+'/tile1.png'))
        self.image_tile.append(pygame.image.load(DATADIR+'/tile2.png'))
        self.image_tile.append(pygame.image.load(DATADIR+'/tile3.png'))
        
        if SFX:
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()

            self.sound['fire0'] = pygame.mixer.Sound(DATADIR+'/fire0.wav')
            self.sound['fire1'] = pygame.mixer.Sound(DATADIR+'/fire1.wav')
            self.sound['fire_bounce0'] = pygame.mixer.Sound(DATADIR+'/fire_bounce0.wav')
            self.sound['powera0'] = pygame.mixer.Sound(DATADIR+'/powera0.wav')

            

            for s in self.sound.itervalues():
                s.set_volume(1.0)

        if MUSIC:
            if not SFX:
                pygame.mixer.pre_init(44100, -16, 1, 512)
                pygame.mixer.init()
            loop=-1 #number of times?
            volume=0.45
            filename = DATADIR+'/'+'music.mp3'
            pygame.mixer.music.load(filename)#self.filepath(filename))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loop)


    def run(self):
        self.host = HOST
        pygame.display.init()
        pygame.font.init()
        pygame.mouse.set_visible(False)
        self.init_data()

        while self.running:
            try:
                self.world.proc()
                self.on_client_entity_collision() #play sfx for bouncing bullets

                self._client.update()
                self.on_logic()
            except Exception, e:
                logging.exception(e)
                self.running = False
                raise
            finally:
                pass
            
            if PRINT_DEBUG_HUD and self.client_focus[0] != 1: pass
            else: self.on_draw()

            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if   event.type == pygame.QUIT: self.running = 0
                elif event.type == pygame.KEYDOWN: self.on_key(keys, event,'down')
                elif event.type == pygame.KEYUP: self.on_key(keys, event,'up')
                elif event.type == pygame.MOUSEBUTTONDOWN: self.on_mouse(event)
                elif event.type == pygame.ACTIVEEVENT:
                    self.client_focus = (event.state,event.gain)
        self._client.disconnect()


if __name__ == '__main__':
    import logging
    logging.basicConfig(filename='client.log', level=logging.ERROR)#CRITICAL)#.DEBUG)
    c = GameClient()
    c.run()
