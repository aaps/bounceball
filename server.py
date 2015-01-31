import os,sys
import threading
import time
import legume
import shared
import random
import math

from config_txt import *

class GameServer():
    def __init__(self):
        self.world = shared.World(1)
        self._server = legume.Server()
        self._server.OnConnectRequest += self.on_connect_request
        self._server.OnMessage += self.on_message
        self.network_timer = time.time()
        self.draw_timer = time.time() #diagnostics
        self.powerup_timer = time.time()
        self.draw_framecount = 0 #diagnostics
        self.entity_updates = set() #partial updates
        self.avatar_updates = set()
        self.player_updates = set()
        self.entity_count = 0 #increment key
        self.entity_spawn_count = 0 #increment key, just for sfx..
        self.player_count = 0 #increment key
        self.full_update_counter = 0
        self.levels = None
        self.current_level = None
        self.port = shared.PORT



    def on_connect_request(self, sender, args):
        pass
        #we do this manually now
        #self.resync_endpoint(sender)

    def on_message(self, sender, msg):
        if msg.MessageTypeID == shared.CreatePlayerCommand.MessageTypeID:   self.spawn_player(msg.player_id.value, msg.player_color.value, msg.name.value)
        elif msg.MessageTypeID == shared.CreateAvatarCommand.MessageTypeID: self.spawn_entity((msg.x.value, msg.y.value), msg.key.value, msg.player_id.value)
        elif msg.MessageTypeID == shared.CreateEntity2Command.MessageTypeID: self.spawn_entity2(msg.entity_id.value, msg.key.value, (msg.x.value, msg.y.value),(msg.tx.value, msg.ty.value))
        elif msg.MessageTypeID == shared.MoveEntity4Command.MessageTypeID:  self.move_entity4(msg.entity_id.value, (msg.tx.value, msg.ty.value), msg.client_frame.value)
        elif msg.MessageTypeID == shared.CreateLevelCommand.MessageTypeID:  self.spawn_level(msg.tiles.value)
        elif msg.MessageTypeID == shared.ResyncCommand.MessageTypeID:       self.resync_endpoint(sender, msg)

    def resync_endpoint(self, sender, args):
        self.send_full_state_to(sender)
        try: sender.send_reliable_message(self.get_level_as_message())
        except: raise

    def init_data(self):
        if 1:
            for x in range(8*2*0): 
                self.spawn_entity(( 64+(((x%38)*64)) ,(64+((x/38)*64)) ), shared.KEY_AVATAR_A)

        l1 = '''
----------------------------------------
----------------------------------------
----------------------------------------
----------------------------------------
-----++++++++++++++++++++++++++++++-----
-----+1111111111111++1111111111111+-----
-----+.............++.............+-----
-----+..2..........11...........2.+-----
-----+.....................++++...+-----
-----+.....................++11...+-----
-----+.....++..++..++..++..++.....+-----
-----+..2..11..11..11..11..11...2.+-----
-----+............................+-----
-----+...........3...3.,..........+-----
-----+......................++....+-----
-----+....++................11....+-----
-----+....++.....3...3............+-----
-----+.2..++....................2.+-----
-----+....+++++++++........++.....+-----
-----+....111111111........11.....+-----
-----+............................+-----
-----+............................+-----
-----+.2.......++...2......++...2.+-----
-----+.........++..........++.....+-----
-----++++++++++++++++++++++++++++++-----
----------------------------------------
----------------------------------------
----------------------------------------
----------------------------------------
----------------------------------------'''.replace('\n','')
        
        self.levels = [l1]
        self.current_level = 0
        self.spawn_level(self.levels[self.current_level])

    #internal funcs
    def get_player_as_message(self, player):
        msg = shared.PlayerUpdate()
        msg.player_id.value = player.player_id
        msg.player_color.value = player.player_color
        msg.entity_id.value = player.entity_id
        msg.kills.value = player.kills
        msg.deaths.value = player.deaths
        msg.score.value = player.score
        msg.winner.value = player.winner
        msg.frame_number.value = self.world._world_frame_number
        msg.name.value = player.name
        return msg

    def _calculate_entity_ahead(self, entity): #creates copy
        e = shared.Entity()
        e.x = (entity.x + entity.vx)
        e.y = (entity.y + entity.vy)
        e.vx = (entity.vx)
        e.vy = (entity.vy)
        e.entity_id = entity.entity_id
        return e

    def get_world_as_message(self):
        msg = shared.WorldUpdate()
        msg.frame_number.value = self.world._world_frame_number
        return msg

    def get_entity_as_message(self, entity, calculate_ahead=False):#True):
        if entity.player_id != 0: #this entity is player, or fired by player
            p = self.world.player.get(entity.player_id) 
            if p is not None: #this player exist
                if p.entity_id == entity.entity_id: #this IS the player, not just a fired projectile
                    return self.get_avatar_as_message(entity, calculate_ahead)

        msg = shared.EntityUpdate()
        msg.entity_id.value = entity.entity_id
        msg.entity_spawn_id.value = entity.entity_spawn_id
        msg.player_id.value = entity.player_id
        msg.key.value = entity.key

        if calculate_ahead: e = self._calculate_entity_ahead(entity)
        else:               e = entity

        msg.x.value = e.x
        msg.y.value = e.y
        msg.vx.value = e.vx
        msg.vy.value = e.vy
        msg.ax.value = e.ax
        msg.ay.value = e.ay
        msg.tx.value = e.tx
        msg.ty.value = e.ty
        msg.release.value = e.release
        msg.hp.value = e.hp
        msg.shield.value = e.shield
        msg.energy.value = e.energy
        msg.client_frame.value = e.client_frame
        if calculate_ahead: msg.frame_number.value = self.world._world_frame_number + 1 #this is needed since server_frame_number cant be set
        else:               msg.frame_number.value = self.world._world_frame_number
        return msg

    def get_avatar_as_message(self, entity, calculate_ahead=False):#True):
        msg = shared.AvatarUpdate()
        msg.entity_id.value = entity.entity_id
        msg.entity_spawn_id.value = entity.entity_spawn_id
        msg.player_id.value = entity.player_id
        msg.key.value = entity.key

        if calculate_ahead: e = self._calculate_entity_ahead(entity)
        else:               e = entity

        msg.x.value = e.x
        msg.y.value = e.y
        msg.vx.value = e.vx
        msg.vy.value = e.vy
        msg.ax.value = e.ax
        msg.ay.value = e.ay
        msg.tx.value = e.tx
        msg.ty.value = e.ty
        msg.release.value = e.release
        msg.hp.value = e.hp
        msg.shield.value = e.shield
        msg.energy.value = e.energy
        msg.client_frame.value = e.client_frame
        if calculate_ahead: msg.frame_number.value = self.world._world_frame_number + 1 #this is needed since server_frame_number cant be set
        else:               msg.frame_number.value = self.world._world_frame_number
        return msg

    def get_level_as_message(self):
        msg = shared.LevelUpdate()
        msg.tiles.value = self.world.tiles_string
        return msg

    #commands player
    def spawn_player(self, player_id, player_color, name):
        print('spawn_player', player_id, player_color, name)
        p = self.world.player.get(player_id)
        if p is None:
            p = shared.Player()
            p.player_id = player_id
            self.player_count += 1
            p.player_color = self.player_count
            p.name = name.encode('ascii','ignore')
            self.world.world_insert_player(p)
            self.player_updates.add(p)
        else:
            p.name = name.encode('ascii','ignore') #update name
            self.world.world_insert_player(p)
            self.player_updates.add(p)

    #commands entity
    def get_new_entity(self):
        if len(self.world.entity_recycle) == 0:
            e = shared.Entity()
            self.entity_count += 1
            e.entity_id = self.entity_count
        else:
            e = next(iter(self.world.entity_recycle)) #get random element
            self.world.entity_recycle.remove(e)
            e.reset()
        self.entity_spawn_count += 1
        e.entity_spawn_id = self.entity_spawn_count
        return e

    #being
    def spawn_entity(self, position, key, player_id=0): #if player_id = controlled by player
        print('spawn_entity', player_id, position)
        e = self.get_new_entity()

        e.key = key
        e.release = 0
        e.x = position[0] * shared.ZONE_SCALE
        e.y = position[1] * shared.ZONE_SCALE

        if player_id != 0 and self.world.player.get(player_id) is not None: # this is player, get spawnpoint
            x,y = self.world.get_random_tile_xy('spawn')
            e.x = (x * shared.TILE_SIZE + shared.TILE_SIZE/2) * shared.ZONE_SCALE
            e.y = (y * shared.TILE_SIZE + shared.TILE_SIZE/2) * shared.ZONE_SCALE
        e.vx = random.randint(-5, 5)
        e.vy = random.randint(-5, 5)

        if e.key == shared.KEY_AVATAR_A:
            e.hp = 60
            e.shield = shared.SHIELD_MAX
            e.energy = shared.ENERGY_MAX
        self.world.world_insert_entity(e)
        if player_id is 0:
            self.entity_updates.add(e)
            print('Spawning entity with ID %s' % (e.debug()))
        else:
            e.player_id = player_id #entity playerid

            p = self.world.player.get(e.player_id)
            if p is not None:
                p.entity_id = e.entity_id #player entity id

            self.avatar_updates.add(e)
            print('Spawning avatar with ID %s' % (e.debug()))
        
    #projectile
    def spawn_entity2(self, entity_id, key, position, target_position): #entity_id = source
        source = self.world.entity.get(entity_id)
        if source is None: return #entity doesnt exist! #fix logg....
        if key == shared.KEY_SHOT_A:
            source.energy -= shared.ENERGY_COST_FIRE_SHOT
            self.entity_updates.add(source)
        player_id = source.player_id
        print('spawn_entity2', entity_id, position, target_position)

        e = self.get_new_entity()
        e.key = key
        e.x = position[0] 
        e.y = position[1] 

        speed = 1000
        dx = (target_position[0]) - position[0]
        dy = (target_position[1]) - position[1]
        len = math.sqrt((dx * dx) + (dy * dy))
        if len == 0.0: len = 0.000001
        e.vx = (dx / len) * speed
        e.vy = (dy / len) * speed
        e.player_id = player_id #'owner'
        e.release = 0
        if e.key == shared.KEY_SHOT_A:
            e.radius = 8
            e.release = self.world._world_frame_number + 60 #SHOT 
        self.world.world_insert_entity(e)

        self.entity_updates.add(e)        
        print('Spawning entity2 with ID %s' % (e.debug()))
        
    def move_entity(self, entity_id, position=None):
        print('move_entity', entity_id, position)
        e = self.world.entity.get(entity_id)
        if e is None:
            return #fix entity does not exist... logg..
        if position is not None:
            e.x = position[0] * shared.ZONE_SCALE
            e.y = position[1] * shared.ZONE_SCALE
        self.world.world_insert_entity(e)
        self.entity_updates.add(e)
        print('Moving entity with ID %s' % (e.debug()))

    def move_entity2(self, entity_id, vel=None):
        print('move_entity2', entity_id, vel)
        e = self.world.entity.get(entity_id)
        if e is None:
            return #fix entity does not exist... logg..
        if vel is not None:
            e.vx = vel[0]
            e.vy = vel[1]
        self.world.world_insert_entity(e)
        self.entity_updates.add(e)
        print('Moving2 entity with ID %s' % (e.debug()))

    def move_entity3(self, entity_id, vel=None):
        print('move_entity3', entity_id, vel)
        e = self.world.entity.get(entity_id)
        if e is None:
            return #fix entity does not exist... logg..
        if vel is not None:
            e.ax = vel[0]
            e.ay = vel[1]
        self.world.world_insert_entity(e)
        self.entity_updates.add(e)
        print('Moving3 entity with ID %s' % (e.debug()))

    def move_entity4(self, entity_id, pos, client_frame):
        frame_diff = self.world._world_frame_number - client_frame 
        if frame_diff < 0 or frame_diff > 200: return #discard check: message is over 200 frames, ...

        print('move_entity4', entity_id, pos)
        e = self.world.entity.get(entity_id)
        if e.client_frame > client_frame: return #discard check: not latest message!... assumtion: only 1 client can move_enteties (server excluded)

        if e is None:
            return #fix entity does not exist... logg..
        if pos is not None:
            e.tx = pos[0]
            e.ty = pos[1]
        signx = math.copysign(1,e.tx - e.x)
        signy = math.copysign(1,e.ty - e.y)
        dx = math.fabs(e.tx - e.x)
        dy = math.fabs(e.ty - e.y)
        e.vx = (dx/19.3 * 0.66 *0.6)*signx
        e.vy = (dy/19.3 * 0.66 *0.6)*signy
        if client_frame != 0:
            e.client_frame = client_frame
        self.world.world_insert_entity(e)
        self.entity_updates.add(e)
        print('Moving4 entity with ID %s' % (e.debug()))

    def spawn_level(self, tiles):
        print('spawn_level')
        self.world.tiles_string = tiles
        self.world.build_level(tiles)
        try: self._server.send_message_to_all(self.get_level_as_message())
        except: raise
        

    def send_entity_updates(self, server):
        partial_list = list(self.entity_updates)
        self.entity_updates = set()
        for e in partial_list:
            logging.debug('**** sending update for entity # %s' % e.entity_id)
            print('Sending update for entity # %s' % e.entity_id)
            e.sync_time = self.world._world_frame_number
            try: server.send_message_to_all(self.get_entity_as_message(e))
            except: raise

    def send_avatar_updates(self, server):
        partial_list = list(self.avatar_updates)
        self.avatar_updates = set()
        for e in partial_list:
            logging.debug('**** sending update for avatar # %s' % e.entity_id)
            print('Sending update for avatar # %s' % e.entity_id)
            e.sync_time = self.world._world_frame_number
            try: server.send_message_to_all(self.get_entity_as_message(e))
            except: raise
    #player
    def send_player_updates(self, server):
        partial_list = list(self.player_updates)
        self.player_updates = set()
        for p in partial_list:
            logging.debug('**** sending update for player # %s' % p.player_id)
            print('Sending update for player # %s' % p.player_id)
            p.sync_time = self.world._world_frame_number
            try: server.send_reliable_message_to_all(self.get_player_as_message(p))
            except: raise

    #all data
    def send_full_state_to(self, endpoint, reliable=True): #fix: bulk ?
        sync_threshold = 30 #must be atleast 30 frames old to be updates
        if reliable:
            try: endpoint.send_reliable_message(self.get_world_as_message())
            except: raise
            for e in self.world.entity.itervalues():                 
                if self.world._world_frame_number - e.sync_time >= sync_threshold:
                    e.sync_time = self.world._world_frame_number
                    try: endpoint.send_reliable_message(self.get_entity_as_message(e,False))
                    except: raise
            for p in self.world.player.itervalues(): 
                if self.world._world_frame_number - p.sync_time >= sync_threshold:
                    p.sync_time = self.world._world_frame_number
                    try: endpoint.send_reliable_message(self.get_player_as_message(p))
                    except: raise
        else:
            try: endpoint.send_message(self.get_world_as_message())
            except: raise
            for e in self.world.entity.itervalues(): 
                if self.world._world_frame_number - e.sync_time >= sync_threshold:
                    e.sync_time = self.world._world_frame_number
                    try: endpoint.send_message(self.get_entity_as_message(e,False))
                    except: raise
            for p in self.world.player.itervalues(): 
                if self.world._world_frame_number - p.sync_time >= sync_threshold:
                    p.sync_time = self.world._world_frame_number
                    try: endpoint.send_message(self.get_player_as_message(p))
                    except: raise

    def send_full_state_to_all(self, endpoint, reliable=True):
        sync_threshold = 30 #must be atleast 30 frames old to be updates
        if reliable:
            try: endpoint.send_reliable_message_to_all(self.get_world_as_message())
            except: raise
            for e in self.world.entity.itervalues(): 
                if self.world._world_frame_number - e.sync_time >= sync_threshold:
                    e.sync_time = self.world._world_frame_number
                    try: endpoint.send_reliable_message_to_all(self.get_entity_as_message(e,False))
                    except: raise
            for p in self.world.player.itervalues(): 
                if self.world._world_frame_number - p.sync_time >= sync_threshold:
                    p.sync_time = self.world._world_frame_number
                    try: endpoint.send_reliable_message_to_all(self.get_player_as_message(p))
                    except: raise
        else:
            try: endpoint.send_message_to_all(self.get_world_as_message())
            except: raise
            for e in self.world.entity.itervalues(): 
                if self.world._world_frame_number - e.sync_time >= sync_threshold:
                    e.sync_time = self.world._world_frame_number
                    try: endpoint.send_message_to_all(self.get_entity_as_message(e,False))
                    except: raise
            for p in self.world.player.itervalues(): 
                if self.world._world_frame_number - p.sync_time >= sync_threshold:
                    p.sync_time = self.world._world_frame_number
                    try: endpoint.send_message_to_all(self.get_player_as_message(p))
                    except: raise

    def run(self):
        self._server.listen(('', self.port))
        print('Listening on port %d' % self.port)

        self.init_data()

        while True:
            # Physics stuff
            try:
                self.world.proc()
            except Exception, e:
                logging.exception(e)
                raise
            for e in self.world.entity_events: self.entity_updates.add(e) #append collisions

            #end game
            win = self.world.get_winner()            
            if len(win) > 0:
                next_game = self.world.get_time_to_next_game(win)
                if next_game == 0:
                    self.current_level = (self.current_level+1)%len(self.levels)
                    try:
                        self.spawn_level(self.levels[self.current_level])
                    except:
                        logging.exception(e)
                        raise

            #powerup
            if time.time() > self.powerup_timer + shared.POWERUP_SPAWN_INTERVAL:                
                if self.world.count_entity_with_key(shared.KEY_POWERUP_A) == 0:
                    self.powerup_timer = time.time()
                    x,y = self.world.get_random_tile_xy('powerup')
                    x = x*shared.TILE_SIZE+shared.TILE_SIZE/2
                    y = y*shared.TILE_SIZE+shared.TILE_SIZE/2
                    self.spawn_entity((x,y), shared.KEY_POWERUP_A)

        
            # Diagnostic
            if time.time() > self.draw_timer + 1.0: #print frames every N seconds
                #print('Frame:',self.world._world_frame_number)
                #print('Delta Frames:', self.world._world_frame_number - self.draw_framecount)
                #print('Delta Time:', time.time() - self.draw_timer)
                self.draw_timer = time.time()
                self.draw_framecount = self.world._world_frame_number

            # Network stuff
            if time.time() > self.network_timer + shared.NETWORK_INTERVAL:
                try:
                    self.network_timer = time.time()
                    self.full_update_counter += 1
                    if self.full_update_counter == shared.FULL_NETWORK_UPDATE_EVERY_N_FRAMES:
                        self.full_update_counter = 0
                        if len(win) > 0 and next_game < 5: pass
                        else: self.send_full_state_to_all(self._server, False)
                    else: 
                        self.send_player_updates(self._server)
                        self.send_avatar_updates(self._server)
                        self.send_entity_updates(self._server)
                except:
                    logging.exception(e)
                    raise

            self._server.update()
            time.sleep(0.001)
        self._server.disconnect()

def main():
    server = GameServer()
    server.run()

if __name__ == '__main__':
    import logging
    logging.basicConfig(filename='server.log', level=logging.ERROR,#CRITICAL,#DEBUG,
        filemode="w",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    main()

