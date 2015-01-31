import time
import legume
import random
import math
import itertools
import pygame

#misc
from uuid import getnode as get_mac
mac = get_mac()
import hashlib
def hashed_int(s): return int(hashlib.md5(s).hexdigest(), 16)
def hashed_int_mod(s,mod): return int(hashed_int(s)%mod)

#config
PORT = 12401

GAME_VERSION = 1

ZONE_SCALE = 100

ZONE_SCREEN_WIDTH = 800
ZONE_SCREEN_HEIGHT = 600

ZONE_WIDTH =  4 * 640  * ZONE_SCALE
ZONE_HEIGHT = 4 * 480 * ZONE_SCALE

TILE_SIZE = 64

NETWORK_INTERVAL = 0.033333333 #30 fps
NETWORK_FRAMES_PER_SECOND = 1.0 / NETWORK_INTERVAL #partial updates
print('Network update rate:', NETWORK_FRAMES_PER_SECOND)
FULL_NETWORK_UPDATE_EVERY_N_FRAMES = int(NETWORK_FRAMES_PER_SECOND*3) #full updates, every 3 seconds

PHYSICS_INTERVAL = 0.01 #100 fps
PHYSICS_FRAMES_PER_SECOND = 1.0 / PHYSICS_INTERVAL
print('Physics update rate:', PHYSICS_FRAMES_PER_SECOND)

CLIENT_LOGIC_INTERVAL = 0.5 #2 fps

GAME_POINTS_TO_WIN = 25
WIN_GAME_TEXT_SECONDS = 10.0 #10 seconds

KEY_MOVE = 1
KEY_SHOT_A = 2
KEY_AVATAR_A = 3
KEY_POWERUP_A = 4
KEY_BOMB_A = 5
KEY_EXPLODE_A = 6

ENERGY_COST_FIRE_SHOT = 40
ENERGY_MAX = 120

POWERUP_SPAWN_INTERVAL = 8.0

SHIELD_MAX = 60

COOLDOWN_SHOTA = 0.66 #2 shot per 3 second

DMG_SHOTA = 50.0

IDLE_VEL = 15

from config_txt import *

#message player
MSGID = legume.messages.BASE_MESSAGETYPEID_USER

class PlayerUpdate(legume.messages.BaseMessage):
    MessageTypeID = MSGID+1
    MessageValues = {
        'player_id' : 'int',
        'player_color' : 'int', #fix not used...
        'entity_id' : 'int',
        'frame_number' : 'int',
        'deaths' : 'int',
        'kills' : 'int',
        'score' : 'int',
        'winner' : 'int',
        'name' : 'string 32'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(PlayerUpdate)

class CreatePlayerCommand(legume.messages.BaseMessage):
    MessageTypeID = MSGID+2
    MessageValues = {
        'player_id' : 'int',
        'player_color' : 'int',
        'name' : 'string 32'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(CreatePlayerCommand)

#message entity
class AvatarUpdate(legume.messages.BaseMessage):
    MessageTypeID = MSGID+3
    MessageValues = {
        'player_id' : 'int',
        'entity_id' : 'int',
        'key' : 'int',
        'frame_number' : 'int',
        'x' : 'int',
        'y' : 'int',
        'vx' : 'int',
        'vy' : 'int',
        'ax' : 'int',
        'ay' : 'int',
        'tx' : 'int',
        'ty' : 'int',
        'client_frame' : 'int',
        'release' : 'int',
        'entity_spawn_id' : 'int',
        'hp' : 'int',
        'shield' : 'int',
        'energy' : 'int'
        }
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(AvatarUpdate)

class EntityUpdate(legume.messages.BaseMessage):
    MessageTypeID = MSGID+4
    MessageValues = {
        'entity_id' : 'int',
        'player_id' : 'int',
        'key' : 'int',
        'frame_number' : 'int',
        'x' : 'int',
        'y' : 'int',
        'vx' : 'int',
        'vy' : 'int',
        'ax' : 'int',
        'ay' : 'int',
        'tx' : 'int',
        'ty' : 'int',
        'client_frame' : 'int',
        'release' : 'int',
        'entity_spawn_id' : 'int',
        'hp' : 'int',
        'shield' : 'int',
        'energy' : 'int'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(EntityUpdate)

class CreateAvatarCommand(legume.messages.BaseMessage):
    MessageTypeID = MSGID+5
    MessageValues = {
        'player_id' : 'int',
        'key' : 'int',
        'x' : 'int',  #fix not used...
        'y' : 'int'}  #fix not used...
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(CreateAvatarCommand)

class CreateEntity2Command(legume.messages.BaseMessage):
    MessageTypeID = MSGID+7
    MessageValues = {
        'entity_id' : 'int',
        'key' : 'int',
        'x' : 'int',
        'y' : 'int',
        'tx' : 'int',
        'ty' : 'int'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(CreateEntity2Command)

class MoveEntity4Command(legume.messages.BaseMessage):
    MessageTypeID = MSGID+11
    MessageValues = {
        'entity_id' : 'int',
        'tx' : 'int',
        'ty' : 'int',
        'client_frame' : 'int'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(MoveEntity4Command)

class WorldUpdate(legume.messages.BaseMessage):
    MessageTypeID = MSGID+12
    MessageValues = {
        'frame_number' : 'int'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(WorldUpdate)

class CreateLevelCommand(legume.messages.BaseMessage):
    MessageTypeID = MSGID+13
    MessageValues = {
        'tiles' : 'varstring'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(CreateLevelCommand)

class LevelUpdate(legume.messages.BaseMessage):
    MessageTypeID = MSGID+14
    MessageValues = {
        'tiles' : 'varstring'}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(LevelUpdate)

class ResyncCommand(legume.messages.BaseMessage):
    MessageTypeID = MSGID+15
    MessageValues = {}
    def __repr__(self): return str(reprobject.getstate2(self))
legume.messages.message_factory.add(ResyncCommand)



class ClientMessage(object):
    MessageTypeID = 0

#client only commands
class ClientSpawnEntityCommand(object):
    MessageTypeID = 1
    def __init__(self):
        self.key = 0
        self.x = 0
        self.y = 0
        self.vx = 0
        self.vy = 0


#util
class reprobject(object):
    @staticmethod
    def getstate2(self):
        attr_and_values = ((attr, getattr(self, attr)) for attr in list(self.MessageValues.keys()) if not attr.startswith("__"))  #only class not subclass        
        d = {attr: value._value for attr, value in attr_and_values if not callable(value)}
        return d

    def getstate(self):
        attr_and_values = ((attr, getattr(self, attr)) for attr in dir(self) if not attr.startswith("__"))
        d = {attr: value for attr, value in attr_and_values if not callable(value)}
        return d

    def __repr__(self):
        return str(self.getstate())

def lerp(a, b, p): #linear interpolate
    return(a+(b-a)*p)

class Tile(object):
    def __init__(self):
        self.tile_data = 0
        self.tile_image = 0

    def __repr__(self):
        return str((self.tile_data, self.tile_image))

#classes
class World(reprobject):
    def __init__(self, is_server):
        self.is_server = is_server
        self.entity = {}
        self.entity_events = set() #partial updates
        self.entity_recycle = set() #removed entety's that can be recycled
        self.client_entity = {} #just client_side, dont collide, used for gfx-effects
        self.player = {}
        self.tiles_x = ZONE_WIDTH / ZONE_SCALE / TILE_SIZE
        self.tiles_y = ZONE_HEIGHT / ZONE_SCALE / TILE_SIZE
        self.tile = [[Tile() for x in range(self.tiles_x)] for y in range(self.tiles_y)]
        self.tiles_string = ''
        self.tile_spawn = {} #(x,y) coords, spawn point
        self.tile_power = {} #(x,y) coords, powerup point
        self._frame_timer = time.time()
        self._frame_accumulator = 0
        self._world_frame_number = 1

        self.quadtree=QuadTree(self,pygame.Rect(0,0,ZONE_WIDTH, ZONE_HEIGHT))
        self.quadtree.level_limit=3

    #player
    def world_insert_player(self, p):
        self.player[p.player_id] = p

    #entity
    def world_insert_entity(self, e):
        self.entity[e.entity_id] = e

    def world_insert_client_entity(self, e):
        self.client_entity[e.entity_id] = e

    def build_level(self, tiles):
        self.entity = {}
        self.entity_events = set()
        self.entity_recycle = set()
        self.client_entity = {}
        self.tile_spawn = {}
        self.tile_power = {}
        for p in self.player.itervalues():
            p.entity_id = 0
            p.kills = 0
            p.deaths = 0
            p.score = 0
            p.winner = 0

        #level
        self.tiles_string = tiles
        col = len(self.tile[0])
        for y in range(len(self.tile)):
            for x in range(col):
                t = tiles[y*col+x]                
                if t == '1':
                    self.tile[y][x].tile_data = 1 #white wall rect
                    self.tile[y][x].tile_image = 1    
                elif t == '2':
                    self.tile[y][x].tile_data = 2 #avatar spawn tile
                    self.tile[y][x].tile_image = 2
                    self.tile_spawn[(x,y)] = 1
                elif t == '3':
                    self.tile[y][x].tile_data = 3 #power-up spawn tile
                    self.tile[y][x].tile_image = 3
                    self.tile_power[(x,y)] = 1
                elif t == '+':
                    self.tile[y][x].tile_data = 1 #white wall tile
                    self.tile[y][x].tile_image = -2
                elif t == '-':
                    self.tile[y][x].tile_data = 0 #black floor rect
                    self.tile[y][x].tile_image = -1
                else: #elif t == '.':
                    self.tile[y][x].tile_data = 0 #grey floor rect
                    self.tile[y][x].tile_image = 0
        if len(self.tile_spawn) == 0: #fix . temp fix if no spawn points are on map
            x,y = (0,0)
            self.tile[y][x].tile_data = 2
            self.tile[y][x].tile_image = 2
            self.tile_spawn[(x,y)] = 1
                    

    #simulation
    def proc(self):
        newtime = time.time()
        deltatime = newtime - self._frame_timer
        self._frame_timer = newtime
        self._frame_accumulator += deltatime

        while self._frame_accumulator >= PHYSICS_INTERVAL:
            #proc elements
            self.entity_events = set()
            self._frame_accumulator -= PHYSICS_INTERVAL

            #server entity
            for e in self.entity.itervalues():
                recycle = e.proc(self, 1)
                if recycle and e not in self.entity_recycle:
                    self.entity_recycle.add(e)
            #client entity
            remove_list = []
            for e in self.client_entity.itervalues():
                remove = e.proc(self, 0)
                if remove: remove_list.append(e)    
            for e in remove_list: del self.client_entity[e.entity_id] #remove

            self.world_collision_detect()
            self._world_frame_number += 1

    def count_entity_with_key(self, key):
        return sum([1 for e in self.entity.itervalues() if e.key == key and e.release == 0])

    def get_random_tile_xy(self, key):
        if key == 'spawn': return random.choice(self.tile_spawn.keys())
        if key == 'powerup': return random.choice(self.tile_power.keys())

    def get_tile_data_xy(self, x, y):
        tx = x / ZONE_SCALE / TILE_SIZE
        ty = y / ZONE_SCALE / TILE_SIZE
        if tx < 0 or tx >= self.tiles_x: return 1 #wall
        if ty < 0 or ty >= self.tiles_y: return 1 #wall
        return self.tile[int(ty)][int(tx)].tile_data

    def world_collision_detect(self):        
        #object
        self.quadtree.test_collisions(self)
        self.quadtree.reset()

        #world - object
        for e in self.entity.itervalues():
            cxy = self.get_tile_data_xy(e.x+e.vx, e.y+e.vy)
            if cxy == 1:
                cx = self.get_tile_data_xy(e.x+e.vx, e.y)
                cy = self.get_tile_data_xy(e.x, e.y+e.vy)
                cx = 1 if cx == 1 else 0
                cy = 1 if cy == 1 else 0
                self.world_collide_object_at_level(e, cxy, cx, cy)

        #world limit
        for e in self.entity.itervalues():
            if e.x < e.radius: 
                if e.vx < 0: e.vx *= -1
                e.x = e.radius
            elif e.x > ZONE_WIDTH -e.radius:
                if e.vx > 0:  e.vx *= -1
                e.x = ZONE_WIDTH - e.radius
            if e.y < e.radius: 
                if e.vy < 0: e.y *= -1
                e.y = e.radius
            elif e.y > ZONE_HEIGHT -e.radius:
                if e.vy > 0: e.vy *= -1
                e.y = ZONE_HEIGHT - e.radius
     

    def world_collide_object_new_method_not_used(self, e1, e2):
        x=(e1.x-e2.x)
        y=(e1.y-e2.y)
        dist = math.sqrt(x**2+y**2)
        if dist<=e1.radius+e2.radius and dist!=0:
            #we collided, act apon it
            self.entity_events.add(e1) #append to event

            x/=dist
            y/=dist
            collide_amount=(e1.radius+e2.radius)-dist
            
            p1=collide_amount/float(e1.radius+e2.radius)
            p2=math.sin(math.radians(    lerp(0,90,p1)    ))

            p=lerp(1,p2,0.5)#the bigger this number, the more squishy the balls are
            
            collide_amount*=p
            e1.vx+=x*collide_amount
            e1.vy+=y*collide_amount

    def win_game(self, player):
        player.winner = self._world_frame_number
        for e in self.entity.itervalues():
            e.release = self._world_frame_number
            self.entity_events.add(e) #append to event

    def get_winner(self):
        winner = [p for p in self.player.values() if p.winner > 0]
        return winner

    def get_time_to_next_game(self, winner):
        next_game_delay = math.fabs(max(0, winner[0].winner + (PHYSICS_FRAMES_PER_SECOND * WIN_GAME_TEXT_SECONDS) - self._world_frame_number))
        next_game_delay = int(next_game_delay/100.0)
        return next_game_delay

    def world_collide_object_object(self,e1,e2):
        if e1.release > 0 and e1.release <= self._world_frame_number: return
        if e2.release > 0 and e2.release <= self._world_frame_number: return
        if e1.player_id == e2.player_id: return #player & players-bullet, or p-bullet and p-bullet dont collide

        if e1.key == KEY_POWERUP_A and e2.key in [KEY_SHOT_A,KEY_BOMB_A,KEY_EXPLODE_A]: return
        if e2.key == KEY_POWERUP_A and e1.key in [KEY_SHOT_A,KEY_BOMB_A,KEY_EXPLODE_A]: return

        self.entity_events.add(e1) #append to event
        o1 = None
        p1 = None
        if e1.key == KEY_AVATAR_A and e2.key in [KEY_SHOT_A,KEY_EXPLODE_A, KEY_POWERUP_A]: #only collide 1 time!
            o1 = e1
            p1 = e2
        if o1 is not None:
            if p1.key == KEY_POWERUP_A:
                pp = [p for p in self.player.itervalues() if p.entity_id == o1.entity_id] #pick up
                pp[0].score += 1
                p1.release = self._world_frame_number
            elif p1.key in [KEY_SHOT_A,KEY_EXPLODE_A]:
                dmg = DMG_SHOTA
                if o1.shield >= dmg: o1.shield -= dmg
                else:
                    dmg -= o1.shield
                    o1.shield = 0
                    if o1.hp > dmg: o1.hp -= dmg
                    else: #dead
                        o1.hp = 0 #-= dmg
                        o1.release = self._world_frame_number
                        #add score                    
                        pp = [p for p in self.player.itervalues() if p.entity_id == o1.entity_id] #death obj
                        if len(pp) > 0:
                            pp[0].deaths += 1
                            pp[0].score -= 2
                            pp2 = [p for p in self.player.itervalues() if p.player_id == pp[0].player_id] #who fired shot
                            if len(pp2) > 0:
                                pp2[0].kills += 1
                                pp2[0].score += 5
                                if pp2[0].score >= GAME_POINTS_TO_WIN:
                                    self.win_game(pp2[0])
        


        mode = 2
        if mode == 1: #half of both vel + mass
            me1 = e1.mass/e2.mass
            me2 = e2.mass/e1.mass
            ve1 = math.sqrt((e1.vx**2)+(e1.vy**2))
            ve2 = math.sqrt((e2.vx**2)+(e2.vy**2))
            v = ( (ve1*me1)  +  (ve2*me2) )/2
        elif mode == 2: #half of both vel
            ve1 = math.sqrt((e1.vx**2)+(e1.vy**2))
            ve2 = math.sqrt((e2.vx**2)+(e2.vy**2))
            v = (ve1+ve2)/2
        elif mode == 3: #keep my own vel, + mass
            v = math.sqrt((e1.vx**2)+(e1.vy**2))

        self.world_collide_object_at(e1, v, e2.x, e2.y)

    def world_collide_object_at(self, e1, v, e2_x, e2_y):
        xdiff = -(e1.x-e2_x)
        ydiff = -(e1.y-e2_y)

        if xdiff > 0:
            if ydiff > 0:
                angle = math.degrees(math.atan(ydiff/xdiff))
                vx = -v*math.cos(math.radians(angle))
                vy = -v*math.sin(math.radians(angle))
            else: #elif ydiff < 0:
                angle = math.degrees(math.atan(ydiff/xdiff))
                vx = -v*math.cos(math.radians(angle))
                vy = -v*math.sin(math.radians(angle))
        elif xdiff < 0:
            if ydiff > 0:
                angle = 180 + math.degrees(math.atan(ydiff/xdiff))
                vx = -v*math.cos(math.radians(angle))
                vy = -v*math.sin(math.radians(angle))
            else: #elif ydiff < 0:
                angle = -180 + math.degrees(math.atan(ydiff/xdiff))
                vx = -v*math.cos(math.radians(angle))
                vy = -v*math.sin(math.radians(angle))
        elif xdiff == 0:
            if ydiff > 0:
                angle = -90
            else:
                angle = 90
            vx = v*math.cos(math.radians(angle))
            vy = v*math.sin(math.radians(angle))
        else:#elif ydiff == 0:
            if xdiff < 0:
                angle = 0
            else:
                angle = 180
            vx = v*math.cos(math.radians(angle))
            vy = v*math.sin(math.radians(angle))
        
        e1.vx = vx
        e1.vy = vy

    def world_collide_object_at_level(self, e1, cxy, cx, cy): #cxy = always 1, cx and cy can be 1
        v = math.sqrt((e1.vx**2)+(e1.vy**2))
        
        if cx and cy or (not cx and not cy):
            x = e1.x + e1.vx
            y = e1.y + e1.vy
        elif cx and not cy:
            x = e1.x + e1.vx
            y = e1.y - e1.vy
        elif not cx and cy:
            x = e1.x - e1.vx
            y = e1.y + e1.vy

        self.entity_events.add(e1) #append to event

        self.world_collide_object_at(e1, v, x, y)



class Entity(reprobject):
    def __init__(self):
        self.entity_id = 0
        self.entity_spawn_id = 0
        self.release = 0 #adsr
        self.reset()

    def reset(self):
        self.player_id = 0
        self.key = 0 #type
        self.x = 0
        self.y = 0
        self.client_x = 0
        self.client_y = 0
        self.vx = 0 #vel
        self.vy = 0
        self.ax = 0 #acc
        self.ay = 0
        self.tx = 0 #target
        self.ty = 0
        self.radius = 16 * ZONE_SCALE
        self.mass = 16
        self.sync_time = 0 #both use, for each own syncing
        self.server_frame = 0 #server use mainly
        self.force_sync = True #client use
        self.client_frame = 0 #client use mainly
        self.hp = 0
        self.shield = 0
        self.energy = 0
        self.rect = None #for quadtree colisions
        self.set_rect()

    def set_rect(self): self.rect = pygame.Rect(self.x-self.radius, self.y-self.radius,self.radius*2,self.radius*2)

    def is_idle(self): return int(abs(self.vx)+abs(self.vy) < IDLE_VEL)
    #simulation
    def proc(self, world, is_server_entity):
        if self.release > 0 and world._world_frame_number >= self.release: 
            if self.entity_id not in [p.entity_id for p in world.player.values()]: 
                return 1
            if world._world_frame_number >= self.release + PHYSICS_FRAMES_PER_SECOND * 5: #respawn after 5 sec
                x,y = world.get_random_tile_xy('spawn')
                self.x = (x * TILE_SIZE + TILE_SIZE/2) * ZONE_SCALE
                self.y = (y * TILE_SIZE + TILE_SIZE/2) * ZONE_SCALE
                self.vx = 0
                self.vy = 0
                if self.key == KEY_AVATAR_A:
                    self.hp = 60
                    self.shield = SHIELD_MAX
                    self.energy = ENERGY_MAX
                self.release = 0
                world.entity_events.add(self) #update me!
                return 0
            else: return 0

        if self.key not in [KEY_SHOT_A]:
            fric = 0.95
            self.vx *= fric
            self.vy *= fric
        if self.key == KEY_AVATAR_A:
            if self.energy < ENERGY_MAX:
                self.energy = min(ENERGY_MAX, self.energy+0.4)
            idle = self.is_idle()
            energy_cost = 40.0
            if idle and self.energy > energy_cost and self.shield < SHIELD_MAX:
                if SHIELD_MAX > self.shield + 10.0:
                    self.shield += 10.0
                    self.energy -= energy_cost
                else:
                    diff = SHIELD_MAX - self.shield
                    self.shield = SHIELD_MAX
                    self.energy -= (diff/10.0)*energy_cost

        self.vx += self.ax #acc
        self.vy += self.ay
        self.client_x += self.vx
        self.client_y += self.vx
        self.x += self.vx
        self.y += self.vy
        self.client_x = self.client_x + (self.x - self.client_x) * 0.5
        self.client_y = self.client_y + (self.y - self.client_y) * 0.5

        self.set_rect()
        if is_server_entity: #only (server) enteties are colliding
            world.quadtree.add_entity(self)
        
        return 0

    #message
    def message(self, msg, full_update=True):
        if ((msg.frame_number.value >= self.server_frame) or
            (time.time() - self.sync_time > 2.0)) or self.force_sync:
            self.force_sync = False
            self.sync_time = time.time()
            self.server_frame = msg.frame_number.value

            self.entity_id = msg.entity_id.value
            self.entity_spawn_id = msg.entity_spawn_id.value
            self.player_id = msg.player_id.value
            self.key = msg.key.value
            if full_update == False:
                self.client_x = self.x
                self.client_y = self.y
            else:
                self.client_x = msg.x.value
                self.client_y = msg.y.value
            self.x = msg.x.value
            self.y = msg.y.value
            self.vx = msg.vx.value
            self.vy = msg.vy.value
            self.ax = msg.ax.value
            self.ay = msg.ay.value
            self.tx = msg.tx.value
            self.ty = msg.ty.value
            self.release = msg.release.value
            self.hp = msg.hp.value
            self.shield = msg.shield.value
            self.energy = msg.energy.value
            self.client_frame = msg.client_frame.value

    def __repr__(self):
        return super(Entity, self).__repr__()

    def debug(self):
        return '%s, %s, %s, %s, %s, %s' % (self.entity_id, self.x, self.y, self.vx, self.vy, self.player_id)#, self.frame_number)



class Player(reprobject):
    def __init__(self):
        self.player_id = 0
        self.player_color = 0
        self.name = 'noname'
        self.entity_id = 0
        self.kills = 0
        self.deaths = 0
        self.score = 0
        self.winner = 0
        #if you add more stuff here... also remember to add to server.get_player_as_message...
        self.sync_time = 0
        self.server_frame = 0
        self.force_sync = True

    def __repr__(self):
        return super(Player, self).__repr__()

    #simulation
    def proc(self):
        pass

    #message
    def message(self, msg, full_update=True):
        if ((msg.frame_number.value >= self.server_frame) or
            (time.time() - self.sync_time > 2.0)) or self.force_sync:
            self.force_sync = False
            self.sync_time = time.time()
            self.server_frame = msg.frame_number.value

            self.player_id = msg.player_id.value #not really needed
            self.player_color = msg.player_color.value
            self.entity_id = msg.entity_id.value
            self.kills = msg.kills.value
            self.deaths = msg.deaths.value
            self.score = msg.score.value
            self.winner = msg.winner.value
            self.name = msg.name.value.encode('ascii','ignore')



#Quad tree code
def rect_quad_split(rect): #slit into 4
    w=rect.width/2.0
    h=rect.height/2.0
    rl=[]
    rl.append(pygame.Rect(float(rect.left), float(rect.top), float(w), float(h)))
    rl.append(pygame.Rect(float(rect.left+w), float(rect.top), float(w), float(h)))
    rl.append(pygame.Rect(float(rect.left), float(rect.top+h), float(w), float(h)))
    rl.append(pygame.Rect(float(rect.left+w), float(rect.top+h), float(w), float(h)))

    return rl

   
class QuadLeaf(object):
    def __init__(self, stage, rect, quadtree, level):
        self.stage = stage
        self.rect=rect #my rect
        self.quadtree = quadtree #root
        self.level=level #my depth

        quadtree.levels[level].append(self) #add me to tree level
        self.branches=None
        self.entities=[]#a list of collidable objects on this leaf
        
    def subdivide(self):
        self.branches=[]
        for rect in rect_quad_split(self.rect):
            b=QuadLeaf(self.stage, rect, self.quadtree, self.level+1)
            self.branches.append(b)
            
    def test_collisions(self, obj):
        for obj2 in self.entities:
            if obj2.rect.colliderect(obj.rect): #if collide
                if [obj,obj2] not in self.quadtree.collisions and [obj2,obj] not in self.quadtree.collisions: #not already collided?
                    self.quadtree.collisions.append([obj, obj2])
        
        if self.level==self.quadtree.level_limit-1: #depth limit reached
            return
        
        if self.branches!=None: #check deeper...
            for b in self.branches:
                b.test_collisions(obj)

    def add_entity(self, obj):
        for obj2 in self.entities:
            if obj2.rect.colliderect(obj.rect):
                if [obj,obj2] not in self.quadtree.collisions and [obj2,obj] not in self.quadtree.collisions: #not already collided?
                    self.quadtree.collisions.append([obj, obj2])
         
        if self.level==self.quadtree.level_limit-1:#if it's hit the limit of levels
            self.entities.append(obj)
            obj.level=int(self.level)
            return

        if self.branches==None:
            self.subdivide()
            
        #check is if the object fits in any sub-branches
        for b in self.branches:
            if b.rect.contains(obj.rect): 
                b.add_entity(obj) #it DOES fit in a branch, hand it to the branch
                return

        #doesn't fit in any of the branches, stays on this level
        self.entities.append(obj)
        obj.level=int(self.level)
        for b in self.branches:
            b.test_collisions(obj)
            
    def render(self):
        pygame.draw.rect(self.stage.screen, [127,127,127], self.rect, 2)
        if self.branches!=None:
            for b in self.branches:
                b.render()
        

class QuadTree(object):
    def __init__(self, stage, stage_rect):
        self.stage = stage
        self.stage_rect=stage_rect

        self.level_limit=3
        self.reset()

    def add_entity(self, obj):
        for obj2 in self.entities:
            if obj2.rect.colliderect(obj.rect):
                if [obj,obj2] not in self.collisions and [obj2,obj] not in self.collisions:
                    self.collisions.append([obj, obj2])

        if self.level_limit<=0:
            self.entities.append(obj)
            obj.level=-1
            return
            
        #check is if the object fits in any branches
        for b in self.branches:
            if b.rect.contains(obj.rect):
                b.add_entity(obj)
                return
        #doesn't fit in any of the branches, stays on main level
        self.entities.append(obj)
        obj.level=-1
        for b in self.branches:
            b.test_collisions(obj)
        

    def test_collisions(self, world):
        #this means that each object will need a collide command
        for c in self.collisions:
            if 0:
                world.world_collide_object_new_method_not_used(c[0],c[1])
                world.world_collide_object_new_method_not_used(c[1],c[0])
            else:
                if c[0] != c[1]:
                    if math.sqrt(  ((c[0].x-c[1].x)**2)  +  ((c[0].y-c[1].y)**2)  ) <= (c[0].radius+c[1].radius):
                        world.world_collide_object_object(c[0],c[1])
                        world.world_collide_object_object(c[1],c[0])

    def reset(self):
        self.levels=[]
        for x in xrange(self.level_limit):
            self.levels.append([])
        self.branches=[]
        if self.level_limit>0:
            for rect in rect_quad_split(self.stage_rect):
                b=QuadLeaf(self.stage, rect, self, 0)
                self.branches.append(b)
        self.entities=[]#a list of all collidable objects on the main level
        self.collisions=[]

    def render(self):
        for branch in self.branches:
            branch.render()