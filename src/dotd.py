import libtcodpy as libtcod
import math
import textwrap
 
#actual size of the window
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
 
#size of the map
MAP_WIDTH = 140
MAP_HEIGHT = 90

#size of view for map scrolling
VIEW_WIDTH = 80
VIEW_HEIGHT = 43
 
#sizes and coordinates relevant for the GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
INVENTORY_WIDTH = 50
 
#parameters for dungeon generator
ROOM_MAX_SIZE = 15
ROOM_MIN_SIZE = 3
MAX_ROOMS = 50
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2

#ai values
AI_INTEREST = 98 #percentage chance per turn that a monster will stay interested in player once out of sight
 
#spell values
HEAL_AMOUNT = 10
RESTORE_MANA_AMOUNT = 10
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
LIGHTNING_COST = 3
CONFUSE_RANGE = 8
CONFUSE_NUM_TURNS = 10
CONFUSE_COST = 2
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12
FIREBALL_COST = 4
ACID_ARROW_DAMAGE = 8
ACID_ARROW_RADIUS = 2
ACID_ARROW_RANGE = 7
ACID_ARROW_COST = 2
MAGIC_MISSLE_DAMAGE = 6
MAGIC_MISSLE_RANGE = 10
MAGIC_MISSLE_COST = 1
BLINK_COST = 5

#prayer values
WAR_LUST_POWER_BONUS = 15
WAR_LUST_DEFENCE_BONUS = 10
WAR_LUST_EV_BONUS = -5
CURSE_POWER_EFFECT = -10
CURSE_DEFENCE_EFFECT = -10
CURSE_EV_EFFECT = -10

#weapon values
CLUB_POWER = 3
DAGGER_POWER = 4
SHORT_SWORD_POWER = 6
MACE_POWER = 7
AXE_POWER = 9
GLOWING_BROAD_SWORD_POWER = 15

#armour values
RAGS_DEFENCE = 2
RAGS_EV = 0
LEATHER_DEFENCE = 3
LEATHER_EV = -1
RING_MAIL_DEFENCE = 4
RING_MAIL_EV = -2
CHAIN_MAIL_DEFENCE = 6
CHAIN_MAIL_EV = -3
PLATE_MAIL_DEFENCE = 10
PLATE_MAIL_EV = -5
MITHRIL_DEFENCE = 15
MITHRIL_EV = 0
TOTEM_EV = 15

ANIMATION_FRAMES = 20 
 
FOV_ALGO = libtcod.FOV_PERMISSIVE_8 #default FOV algorithm
FOV_LIGHT_WALLS = True  #light walls or not
TORCH_RADIUS = 10
 
LIMIT_FPS = 20  #20 frames-per-second maximum
 
color_dark_wall = libtcod.light_grey
color_light_wall = libtcod.white
color_dark_ground = libtcod.black
color_light_ground = libtcod.darker_grey
 

class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
 
        #all tiles start unexplored
        self.explored = False
 
        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight
 
class Rect:
    #a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
 
    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)
 
    def intersect(self, other):
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)
 
class Object:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, item=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self
 
        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self
 
        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self
 
    def move(self, dx, dy):
        #move by the given amount, if the destination is not blocked
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy
 
    def move_towards(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        ddx = 0 
        ddy = 0
        if dx > 0:
            ddx = 1
        elif dx < 0:
            ddx = -1
        if dy > 0:
            ddy = 1
        elif dy < 0:
            ddy = -1
        if not is_blocked(self.x + ddx, self.y + ddy):
            self.move(ddx, ddy)
        else:
            if ddx != 0:
                if not is_blocked(self.x + ddx, self.y):
                    self.move(ddx, 0)
                    return
            if ddy != 0:
                if not is_blocked(self.x, self.y + ddy):
                    self.move(0, ddy)
                    return
        
    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)
 
    def distance(self, x, y):
        #return the distance to some coordinates
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
 
    def send_to_back(self):
        #make this object be drawn first, so all others appear above it if they're in the same tile.
        global objects
        objects.remove(self)
        objects.insert(0, self)
 
    def send_to_front(self):
        #make this object be drawn last, so it appears above all other objects in the same tile.
        global objects
        objects.remove(self)
        objects.append(self)
 
    def draw(self):
        #only show if it's visible to the player
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            #set the color and then draw the character that represents this object at its position
            vx = player.x - self.x + (VIEW_WIDTH / 2)
            vy = player.y - self.y + (VIEW_HEIGHT / 2)
            libtcod.console_set_foreground_color(con, self.color)
            libtcod.console_put_char(con, vx, vy, self.char, libtcod.BKGND_NONE)
 
    def clear(self):
        #erase the character that represents this object
        vx = player.x - self.x + (VIEW_WIDTH / 2)
        vy = player.y - self.y + (VIEW_HEIGHT / 2)
        libtcod.console_put_char(con, vx, vy, ' ', libtcod.BKGND_NONE)
 
 
class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, mana, piety, defence, power, evasion, death_function=None, timer = 0, status_effect=None):
        self.max_hp = hp
        self.hp = hp
        self.max_mana = mana
        self.mana = mana
        self.max_piety = piety
        self.piety = piety
        self.max_defence = defence
        self.defence = defence
        self.max_power = power
        self.power = power
        self.max_evasion = evasion
        self.evasion = evasion
        self.death_function = death_function
        self.timer = timer
        self.status_effect = status_effect
 
    def attack(self, target):
        #a simple formula for attack damage
        damage = 0
        if libtcod.random_get_int(0, 0, 50) > target.fighter.evasion:
            damage = (libtcod.random_get_int(0, 0, self.power + 5) - libtcod.random_get_int(0, 0, target.fighter.defence)) / 2
            if damage > 0:
                #make the target take some damage
                message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
                target.fighter.take_damage(damage)
            else:
                message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but does no damage!')
        else:
            message(self.owner.name.capitalize() + ' attacks but ' + target.name + ' dodges the blow!')
 
    def take_damage(self, damage):
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
 
            #check for death. if there's a death function, call it
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
 
    def heal(self, amount):
        #heal by the given amount, without going over the maximum
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
            
    def restore_mana(self, amount):
        #restore mana by the given amount, without going over the maximum
        self.mana += amount
        if self.mana > self.max_mana:
            self.mana = self.max_mana            

    def restore_piety(self, amount):
        #restore piety by the given amount, without going over the maximum
        self.piety += amount
        if self.piety > self.max_piety:
            self.piety = self.max_piety                        
            
    def use_mana(self, amount):
        #use mana by the given amount
        self.mana -= amount

    def use_piety(self, amount):
        #use piety by the given amount
        self.piety -= amount
        
class BasicMonster:
    memory_x = None
    memory_y = None
        
    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn. if you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y) and player.fighter.status_effect != 'invisible':
            self.memory_x = player.x
            self.memory_y = player.y
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
 
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)
        elif self.memory_x != None and self.memory_y != None: #if can't see player but has a memory of player
            monster.move_towards(self.memory_x, self.memory_y)
            if monster.x == self.memory_x and monster.y == self.memory_y or libtcod.random_get_int(0, 0, 100) > AI_INTEREST:
                self.memory_x = None
                self.memory_y = None
        else: #fake a memory so the monster wanders to location in line of sight
            while True:
                x = libtcod.random_get_int(0, monster.x - 20, monster.x + 20)
                y = libtcod.random_get_int(0, monster.y - 20, monster.y + 20)
                if can_walk_between(monster.x, monster.y, x, y): break
            self.memory_x = x
            self.memory_y = y
 
class ConfusedMonster:
    #AI for a temporarily confused monster (reverts to previous AI after a while).
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns
 
    def take_turn(self):
        if self.num_turns > 0:  #still confused...
            #move in a random direction, and decrease the number of turns confused
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.num_turns -= 1
 
        else:  #restore the previous AI (this one will be deleted because it's not referenced anymore)
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)
 
 
class Item:

    #an item that can be picked up and used or equipped.
    def __init__(self, use_function=None, equip_type=None, power=None, defence=None, evasion=None):
        self.use_function = use_function
        self.equip_type = equip_type
        self.power = power
        self.defence = defence
        self.evasion = evasion
 
    def pick_up(self):
        #add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', libtcod.green)
 
    def drop(self):
        #add to the map and remove from the player's inventory. also, place it at the player's coordinates
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
 
    def use(self):
        #just call the "use_function" if it is defined
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner)  #destroy after use, unless it was cancelled for some reason

    def equip(self):
        global weapon, armour, jewellery
        if self.equip_type == 'weapon':
            if weapon != None:
                inventory.append(weapon)
                message('You put away the ' + weapon.name + '.', libtcod.red)
                weapon = None                
            weapon = self.owner
            inventory.remove(self.owner)
            message('You wield a ' + self.owner.name + '.', libtcod.red)
            calc_stats()
        
        if self.equip_type == 'armour':
            if armour != None:
                inventory.append(armour)
                message('You take off the ' + armour.name + '.', libtcod.red)
                armour = None                
            armour = self.owner
            inventory.remove(self.owner)
            message('You put on the ' + self.owner.name + '.', libtcod.red)
            calc_stats()

        if self.equip_type == 'jewellery':
            if jewellery != None:
                inventory.append(jewellery)
                message('You take off the ' + jewellery.name + '.', libtcod.red)
                armour = None                
            jewellery = self.owner
            inventory.remove(self.owner)
            message('You put on the ' + self.owner.name + '.', libtcod.red)
            calc_stats()
            
        if self.equip_type is None:
            message('The ' + self.owner.name + ' cannot be equipped.')

    def remove(self):
        global weapon, armour, jewellery
        if self.equip_type == 'weapon':
            inventory.append(self.owner)
            weapon = None
            message('You put away the ' + self.owner.name + '.', libtcod.red)
            calc_stats()
        
        if self.equip_type == 'armour':
            inventory.append(self.owner)
            armour = None
            message('You take off the ' + self.owner.name + '.', libtcod.red)
            calc_stats()
            
        if self.equip_type == 'jewellery':
            inventory.append(self.owner)
            jewellery = None
            message('You take off the ' + self.owner.name + '.', libtcod.red)
            calc_stats()
                
def can_walk_between(x1, y1, x2, y2):
    libtcod.line_init(x1, y1, x2, y2)
    test = True
    while True:
        (x, y) = libtcod.line_step()
        if x is None: break
        
        if is_blocked(x, y): 
            test = False
            break
    return test        
        
                
def calc_stats():
    player.fighter.power = player.fighter.max_power
    if weapon != None:
        player.fighter.power = player.fighter.power + weapon.item.power
    if jewellery != None:
        if jewellery.item.power != None:
            player.fighter.power = player.fighter.power + jewellery.item.power

    player.fighter.defence = player.fighter.max_defence
    if armour != None:
        player.fighter.defence = player.fighter.defence + armour.item.defence
    if jewellery != None:
        if jewellery.item.defence != None:
            player.fighter.defence = player.fighter.defence + jewellery.item.defence
            
    player.fighter.evasion = player.fighter.max_evasion
    if armour != None:
        player.fighter.evasion = player.fighter.evasion + armour.item.evasion
    if jewellery != None:
        if jewellery.item.evasion != None:
            player.fighter.evasion = player.fighter.evasion + jewellery.item.evasion

    if player.fighter.status_effect == 'war_lust':
        player.fighter.power = player.fighter.power + WAR_LUST_POWER_BONUS
        player.fighter.defence = player.fighter.defence + WAR_LUST_DEFENCE_BONUS
        player.fighter.evasion = player.fighter.evasion + WAR_LUST_EV_BONUS
        
    if player.fighter.status_effect == 'cursed':
        player.fighter.power = player.fighter.power + CURSE_POWER_EFFECT
        player.fighter.defence = player.fighter.defence + CURSE_DEFENCE_EFFECT
        player.fighter.evasion = player.fighter.evasion + CURSE_EV_EFFECT    
        
    if player.fighter.power < 0: player.fighter.power = 0
    if player.fighter.defence < 0: player.fighter.defence = 0
    if player.fighter.evasion < 0: player.fighter.evasion = 0
            
def is_blocked(x, y):
    #first test the map tile
    if map[x][y].blocked:
        return True
 
    #now check for any blocking objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
 
    return False
 
def create_room(room):
    global map
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False
 
def create_h_tunnel(x1, x2, y):
    global map
    #horizontal tunnel. min() and max() are used in case x1>x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
 
def create_v_tunnel(y1, y2, x):
    global map
    #vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
    
def make_map():
    global map, player
    
    #fill map with "blocked" tiles
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]
 
    rooms = []
    num_rooms = 0
 
    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)
 
        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)
 
        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
 
        if not failed:
            #this means there are no intersections, so this room is valid
 
            #"paint" it to the map's tiles
            create_room(new_room)
 
            #add some contents to this room, such as monsters
            place_objects(new_room)
 
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
 
            if num_rooms == 0:
                #this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel
 
                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()
 
                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)
 
            #append the new room to the list
            rooms.append(new_room)
            num_rooms += 1
            
    #and then place stairs to the next level somewhere in the center of a room!
    if level < 5:
        end_room = libtcod.random_get_int(0, 0, len(rooms) - 1)
        (stair_x, stair_y) = rooms[end_room].center()
        stairs = Object(stair_x, stair_y, '<', 'stairs leading upwards', libtcod.white, False)
        objects.append(stairs)
        
    #place the boss for that level!
    #choose random spot for this monster
    monster = create_leader()
    objects.append(monster)    
  
def place_objects(room):
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)
 
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y) and x != player.x and y != player.y:
            monster_type = libtcod.random_get_int(0, 0, 100)
            if monster_type < 20:
                monster = create_halfling(x, y)
            
            elif monster_type < 40:
                monster = create_gnome(x, y)
            
            elif monster_type < 60:
                monster = create_dwarf(x, y)
            
            elif monster_type < 80:
                monster = create_elf(x, y)
            
            else:
                monster = create_human(x, y)
            
            objects.append(monster)
 
    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)
 
    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            dice = libtcod.random_get_int(0, 0, 100)
            if dice < 30:
                #create a healing potion
                item_component = Item(use_function=cast_heal)
                item = Object(x, y, '!', 'healing potion', libtcod.yellow, item=item_component)
                
            elif dice < 30+20:
                #create a mana potion
                item_component = Item(use_function=cast_restore_mana)
                item = Object(x, y, '!', 'mana potion', libtcod.light_violet, item=item_component)

            elif dice < 50+5:
                #create a lightning bolt scroll
                item_component = Item(use_function=cast_lightning)
                item = Object(x, y, '?', 'scroll of lightning bolt', libtcod.white, item=item_component)
 
            elif dice < 55+5:
                #create a fireball scroll
                item_component = Item(use_function=cast_fireball) 
                item = Object(x, y, '?', 'scroll of fireball', libtcod.red, item=item_component)
                
            elif dice < 60+5:
                #create a confuse scroll
                item_component = Item(use_function=cast_confuse) 
                item = Object(x, y, '?', 'scroll of confusion', libtcod.green, item=item_component)

            elif dice < 65+5:
                #create an acid arrow scroll
                item_component = Item(use_function=cast_acid_arrow) 
                item = Object(x, y, '?', 'scroll of acid arrow', libtcod.light_chartreuse, item=item_component)

            elif dice < 70+5:
                #create a magic missle scroll
                item_component = Item(use_function=cast_magic_missle) 
                item = Object(x, y, '?', 'scroll of magic missle', libtcod.light_magenta, item=item_component)

            elif dice < 75 + 5:
                #create a blink scroll
                item_component = Item(use_function=cast_blink) 
                item = Object(x, y, '?', 'scroll of blink', libtcod.cyan, item=item_component)

            elif dice < 80 + 2:
                #create a club
                item_component = Item(equip_type='weapon', power = CLUB_POWER) 
                item = Object(x, y, ')', 'club', libtcod.light_orange, item=item_component)
                
            elif dice < 82 + 2:
                #create a dagger
                item_component = Item(equip_type='weapon', power = DAGGER_POWER) 
                item = Object(x, y, ')', 'dagger', libtcod.light_sky, item=item_component)

            elif dice < 84 + 2:
                #create a short sword
                item_component = Item(equip_type='weapon', power = SHORT_SWORD_POWER) 
                item = Object(x, y, ')', 'short sword', libtcod.sky, item=item_component)
                
            elif dice < 86 + 2:
                #create a mace
                item_component = Item(equip_type='weapon', power = MACE_POWER) 
                item = Object(x, y, ')', 'mace', libtcod.light_blue, item=item_component)
                
            elif dice < 88 + 2:
                #create a axe
                item_component = Item(equip_type='weapon', power = AXE_POWER) 
                item = Object(x, y, ')', 'axe', libtcod.cyan, item=item_component)
                
            elif dice < 90 + 2:
                #create filthy rags
                item_component = Item(equip_type='armour', defence = RAGS_DEFENCE, evasion = RAGS_EV) 
                item = Object(x, y, ']', 'filthy tunic', libtcod.light_red, item=item_component)

            elif dice < 92 + 2:
                #create a leather armour
                item_component = Item(equip_type='armour', defence = LEATHER_DEFENCE, evasion = LEATHER_EV) 
                item = Object(x, y, ']', 'leather armour', libtcod.orange, item=item_component)

            elif dice < 94 + 2:
                #create a ring mail
                item_component = Item(equip_type='armour', defence = RING_MAIL_DEFENCE, evasion = RING_MAIL_EV) 
                item = Object(x, y, ']', 'ring mail armour', libtcod.light_blue, item=item_component)

            elif dice < 96 + 2:
                #create a chain mail
                item_component = Item(equip_type='armour', defence = CHAIN_MAIL_DEFENCE, evasion = CHAIN_MAIL_EV) 
                item = Object(x, y, ']', 'chain mail armour', libtcod.sky, item=item_component)
    
            else:
                #create a plate armour
                item_component = Item(equip_type='armour', defence = PLATE_MAIL_DEFENCE, evasion = PLATE_MAIL_EV) 
                item = Object(x, y, ']', 'plate mail armour', libtcod.blue, item=item_component)
                
            objects.append(item)
            item.send_to_back()  #items appear below other objects
 
def create_halfling(x, y):
    #create an halfling
    dice = libtcod.random_get_int(0, level, level * 4 + 5) #formula to try and distribute monster strength based on level
    if dice < 8:
        fighter_component = Fighter(hp=6, mana = 10, piety = 10, defence=5, power=5, evasion=15, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'h', 'halfling forager', libtcod.yellow, blocks=True, fighter=fighter_component, ai=ai_component)
    elif dice < 16:
        fighter_component = Fighter(hp=9, mana = 10, piety = 10, defence=7, power=7, evasion=18, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'h', 'halfling thug', libtcod.green, blocks=True, fighter=fighter_component, ai=ai_component)
    else:
        fighter_component = Fighter(hp=12, mana = 10, piety = 10, defence=9, power=9, evasion=21, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'h', 'halfling warden', libtcod.light_blue, blocks=True, fighter=fighter_component, ai=ai_component)
    return monster

def create_gnome(x, y):
    #create a gnome
    dice = libtcod.random_get_int(0, level * 2, level * 4 + 5) #formula to try and distribute monster strength based on level
    if dice < 8:
        fighter_component = Fighter(hp=10, mana = 15, piety = 15, defence=7, power=7, evasion=10, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'g', 'gnome worker', libtcod.yellow, blocks=True, fighter=fighter_component, ai=ai_component)
    elif dice < 16:
        fighter_component = Fighter(hp=13, mana = 15, piety = 15, defence=9, power=9, evasion=12, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'g', 'gnome sapper', libtcod.green, blocks=True, fighter=fighter_component, ai=ai_component)
    else:
        fighter_component = Fighter(hp=16, mana = 15, piety = 15, defence=11, power=11, evasion=14, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'g', 'gnome guard', libtcod.light_blue, blocks=True, fighter=fighter_component, ai=ai_component)
    return monster
    
def create_dwarf(x, y):
    #create a dwarf
    dice = libtcod.random_get_int(0, level * 2, level * 4 + 5) #formula to try and distribute monster strength based on level
    if dice < 8:
        fighter_component = Fighter(hp=13, mana = 5, piety = 10, defence=15, power=15, evasion=5, death_function=monster_death)
        ai_component = BasicMonster() 
        monster = Object(x, y, 'd', 'dwarf miner', libtcod.yellow, blocks=True, fighter=fighter_component, ai=ai_component)    
    elif dice < 16:
        fighter_component = Fighter(hp=17, mana = 5, piety = 10, defence=18, power=17, evasion=5, death_function=monster_death)
        ai_component = BasicMonster() 
        monster = Object(x, y, 'd', 'dwarf brute', libtcod.green, blocks=True, fighter=fighter_component, ai=ai_component)    
    else:
        fighter_component = Fighter(hp=21, mana = 5, piety = 10, defence=21, power=19, evasion=5, death_function=monster_death)
        ai_component = BasicMonster() 
        monster = Object(x, y, 'd', 'dwarf knight', libtcod.light_blue, blocks=True, fighter=fighter_component, ai=ai_component)    
    return monster

def create_elf(x, y):
    #create a elf
    dice = libtcod.random_get_int(0, level * 2, level * 4 + 5) #formula to try and distribute monster strength based on level
    if dice < 8:
        fighter_component = Fighter(hp=8, mana = 15, piety = 15, defence=5, power=7, evasion=15, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'e', 'elf scout', libtcod.yellow, blocks=True, fighter=fighter_component, ai=ai_component)
    elif dice < 16:
        fighter_component = Fighter(hp=11, mana = 15, piety = 15, defence=7, power=9, evasion=18, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'e', 'elf hunter', libtcod.green, blocks=True, fighter=fighter_component, ai=ai_component)
    else:
        fighter_component = Fighter(hp=14, mana = 15, piety = 15, defence=9, power=11, evasion=21, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'e', 'elf duellist', libtcod.light_blue, blocks=True, fighter=fighter_component, ai=ai_component)
    return monster
    
def create_human(x, y):
    #create a human
    dice = libtcod.random_get_int(0, level * 2, level * 4 + 5) #formula to try and distribute monster strength based on level
    if dice < 8:
        fighter_component = Fighter(hp=12, mana = 10, piety = 10, defence=10, power=10, evasion=10, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'H', 'human recruit', libtcod.yellow, blocks=True, fighter=fighter_component, ai=ai_component)
    elif dice < 16:
        fighter_component = Fighter(hp=16, mana = 10, piety = 10, defence=12, power=12, evasion=12, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'H', 'human soldier', libtcod.green, blocks=True, fighter=fighter_component, ai=ai_component)
    else:
        fighter_component = Fighter(hp=20, mana = 10, piety = 10, defence=14, power=14, evasion=14, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(x, y, 'H', 'human paladin', libtcod.light_blue, blocks=True, fighter=fighter_component, ai=ai_component)
    return monster
    
def create_leader():
    global level
    leader_x = 0
    leader_y = 0
    while is_blocked(leader_x, leader_y):
        leader_x = libtcod.random_get_int(0, 1, MAP_WIDTH-1)
        leader_y = libtcod.random_get_int(0, 1, MAP_HEIGHT-1)
 
    if level == 1:
        #create a halfling leader
        fighter_component = Fighter(hp=16, mana = 10, piety = 10, defence=10, power=10, evasion=25, death_function=leader_death)
        ai_component = BasicMonster()
        monster = Object(leader_x, leader_y, 'h', 'halfling elder', libtcod.red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif level == 2:
        #create a gnome leader
        fighter_component = Fighter(hp=24, mana = 15, piety = 15, defence=14, power=14, evasion=10, death_function=leader_death)
        ai_component = BasicMonster()
        monster = Object(leader_x, leader_y, 'g', 'gnome sergeant', libtcod.red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif level == 3:
        #create an elf leader
        fighter_component = Fighter(hp=20, mana = 15, piety = 15, defence=10, power=10, evasion=30, death_function=leader_death)
        ai_component = BasicMonster()
        monster = Object(leader_x, leader_y, 'e', 'elf captain', libtcod.red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif level == 4:
        #create a dwarf leader
        fighter_component = Fighter(hp=32, mana = 5, piety = 10, defence=30, power=30, evasion=5, death_function=leader_death)
        ai_component = BasicMonster() 
        monster = Object(leader_x, leader_y, 'd', 'dwarf warleader', libtcod.red, blocks=True, fighter=fighter_component, ai=ai_component)
    elif level == 5:
        #create a human leader
        fighter_component = Fighter(hp=28, mana = 10, piety = 10, defence=20, power=20, evasion=20, death_function=victory_death)
        ai_component = BasicMonster()
        monster = Object(leader_x, leader_y, 'H', 'human general', libtcod.red, blocks=True, fighter=fighter_component, ai=ai_component)
    return monster
    
def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)
 
    #render the background first
    libtcod.console_set_background_color(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False)
 
    #now render the bar on top
    libtcod.console_set_background_color(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False)
        
    #finally, some centered text with the values
    libtcod.console_set_foreground_color(panel, libtcod.white)
    libtcod.console_print_center(panel, x + total_width / 2, y, libtcod.BKGND_NONE, name + ': ' + str(value) + '/' + str(maximum))
    
    
def get_names_under_mouse():
    #return a string with the names of all objects under the mouse
    mouse = libtcod.mouse_get_status()
    (x, y) = (mouse.cx, mouse.cy)
 
    #create a list with the names of all objects at the mouse's coordinates and in FOV
    names = [obj.name for obj in objects
        if player.x - obj.x + VIEW_WIDTH / 2 == x and player.y - obj.y + VIEW_HEIGHT / 2 == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
 
    names = ', '.join(names)  #join the names, separated by commas
    return names.capitalize()
 
def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute
 
    #go through and clear view for every square to prevent artifacts - messy programming but i don't care!         
    for y in range(VIEW_HEIGHT):
        for x in range(VIEW_WIDTH):
            libtcod.console_put_char_ex(con, x, y, ' ', libtcod.black, libtcod.black)
    
    if fov_recompute:
        #recompute FOV if needed (the player moved or something)
        fov_recompute = True #originally set to false but changed because fov needs to be recomputed every turn for neatness!
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

#go through all tiles, and set their background color according to the FOV
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                vx = player.x - x + (VIEW_WIDTH / 2)
                vy = player.y - y + (VIEW_HEIGHT / 2)
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = map[x][y].block_sight
                if vx in range(0, VIEW_WIDTH) and vy in range(0, VIEW_HEIGHT): 
                    if not visible:
                        #if it's not visible right now, the player can only see it if it's explored
                        if map[x][y].explored:
                            if wall:
                                libtcod.console_set_back(con, vx, vy, color_dark_wall, libtcod.BKGND_SET)
                            else:
                                libtcod.console_set_back(con, vx, vy, color_dark_ground, libtcod.BKGND_SET)
                    else:
                        #it's visible
                        if wall:
                            libtcod.console_set_back(con, vx, vy, color_light_wall, libtcod.BKGND_SET )
                        else:
                            libtcod.console_set_back(con, vx, vy, color_light_ground, libtcod.BKGND_SET )
                        #since it's visible, explore it
                        map[x][y].explored = True
                    
    #draw all objects in the list, except the player. we want it to
    #always appear over all other objects! so it's drawn later.
    #iterate twice, drawing items first and monsters second so that
    #monsters always appear on top of items
    for object in objects:
        if object != player and object.ai == None:
            vx = player.x - object.x + (VIEW_WIDTH / 2)
            vy = player.y - object.y + (VIEW_HEIGHT / 2)
            if vx in range(0, VIEW_WIDTH) and vy in range(0, VIEW_HEIGHT):
                object.draw()
    for object in objects:
        if object != player and object.ai != None:
            vx = player.x - object.x + (VIEW_WIDTH / 2)
            vy = player.y - object.y + (VIEW_HEIGHT / 2)
            if vx in range(0, VIEW_WIDTH) and vy in range(0, VIEW_HEIGHT):
                object.draw()            
    player.draw()
 
    #blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, VIEW_WIDTH, VIEW_HEIGHT, 0, 0, 0)
 
 
    #prepare to render the GUI panel
    libtcod.console_set_background_color(panel, libtcod.black)
    libtcod.console_clear(panel)
 
    #print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_foreground_color(panel, color)
        libtcod.console_print_left(panel, MSG_X, y, libtcod.BKGND_NONE, line)
        y += 1
 
    #show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
        libtcod.red, libtcod.darker_red)
    render_bar(1, 2, BAR_WIDTH, 'MANA', player.fighter.mana, player.fighter.max_mana,
        libtcod.blue, libtcod.darker_blue)
    render_bar(1, 3, BAR_WIDTH, 'PIETY', player.fighter.piety, player.fighter.max_piety, libtcod.green, libtcod.dark_green)
        
    #render additional stats for debug - possible removal in future
    libtcod.console_print_left(panel, 1, 4, libtcod.BKGND_NONE, 'Power: ' + str(player.fighter.power))
    libtcod.console_print_left(panel, 1, 5, libtcod.BKGND_NONE, 'Defence: ' + str(player.fighter.defence))
    libtcod.console_print_left(panel, 1, 6, libtcod.BKGND_NONE, 'Evasion: ' + str(player.fighter.evasion))    
    #display names of objects under the mouse
    libtcod.console_set_foreground_color(panel, libtcod.light_gray)
    libtcod.console_print_left(panel, 1, 0, libtcod.BKGND_NONE, get_names_under_mouse())
 
    #blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
 
 
def message(new_msg, color = libtcod.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
 
    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
 
        #add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )
 
 
def player_move_or_attack(dx, dy):
    global fov_recompute
 
    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy
 
    #try to find an attackable object there
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break
 
    #attack if target found, move otherwise
    if target is not None:
        player.fighter.attack(target)
    else:
        player.move(dx, dy)
        fov_recompute = True

def player_rest():
    global fov_recompute
    fov_recompute = True
        
 
def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
 
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_height_left_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    height = len(options) + header_height
 
    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)
 
    #print the header, with auto-wrap
    libtcod.console_set_foreground_color(window, libtcod.white)
    libtcod.console_print_left_rect(window, 0, 0, width, height, libtcod.BKGND_NONE, header)
 
    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_left(window, 0, y, libtcod.BKGND_NONE, text)
        y += 1
        letter_index += 1
 
    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
 
    #present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
 
    #convert the ASCII code to an index; if it corresponds to an option, return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None
 
def inventory_menu(header):
    #show a menu with each item of the inventory as an option
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = [item.name for item in inventory]
 
    index = menu(header, options, INVENTORY_WIDTH)
 
    #if an item was chosen, return it
    if index is None or len(inventory) == 0: return None
    return inventory[index].item

def equipment_menu(header):
    #show a menu with each item of equipped items as an option 
    options = []
    if weapon is None:
        options.append('No weapon equipped.')
    else:
        options.append(weapon.name)
    if armour is None:
        options.append('No armour equipped.')
    else:
        options.append(armour.name)
    if jewellery is None:
        options.append('No jewellery equipped.')
    else:
        options.append(jewellery.name)
         
    index = menu(header, options, INVENTORY_WIDTH)
 
    #if an item was chosen, return it
    if index is None: 
        return None
    elif index == 0: #weapon
        if weapon is not None: 
            return weapon.item
        else: return None
    elif index == 1: #armour
        if armour is not None:
            return armour.item
        else: return None
    elif index == 2: #jewellery
        if jewellery is not None:
            return jewellery.item
        else: return None
    
def starting_menu():
    #starting menu with intro text and race choices
    options = ['Orc', 'Kobold', 'Goblin']
    index = -1
    while index not in range(0, 3):
        index = menu('Choose your race:', options, 20)
    return index

def starting_text():
    #starting text during intro screen
    libtcod.console_set_foreground_color(con,libtcod.red)
    libtcod.console_print_center(con, 40, 3, libtcod.BKGND_NONE, 'DEFENDER OF THE DEEP')
    libtcod.console_set_foreground_color(con,libtcod.white)
    libtcod.console_print_center_rect(con, 40, 7, 60, 40, libtcod.BKGND_NONE, 'The encroachment of the "civilized" races continues without relent. The creatures scorned by those from the surface took shelter deep within the twisting caverns - hoping to escape the attention of the murderers who had tormented their ancestors for generations. However, the years of peace could not last - eventually the attentions of evil from above found its way into the territory which your people call home. One was chosen to venture forth to strike deep into the heart of the camp of their enemies...')
    libtcod.console_print_center_rect(con, 15, 35, 20, 10, libtcod.BKGND_NONE, 'Orcs are powerful warriors, able to call upon the power of their bloodthirsty gods to enter a state of warlust.')
    libtcod.console_print_center_rect(con, 40, 35, 22, 10, libtcod.BKGND_NONE, 'Kobolds make nimble and dangerous enemies, dodging the blows of their enemies as they strike from the shadows.')
    libtcod.console_print_center_rect(con, 65, 35, 20, 10, libtcod.BKGND_NONE, 'Goblins are famed for their craftiness and cunning, they are physically small but can prove surprisingly lethal.')
    libtcod.console_blit(con, 0, 0, VIEW_WIDTH, VIEW_HEIGHT, 0, 0, 0)
    
def handle_keys():
    key = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
    key_char = chr(key.c)
 
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        #Alt+Enter: toggle fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
 
    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'  #exit game
 
    if game_state == 'playing':
        #movement keys
        if key.vk == libtcod.KEY_KP1 or key_char == 'b':
            player_move_or_attack(1, -1)
 
        elif key.vk == libtcod.KEY_KP2 or key_char == 'j':
            player_move_or_attack(0, -1)
 
        elif key.vk == libtcod.KEY_KP3 or key_char == 'n':
            player_move_or_attack(-1, -1)
 
        elif key.vk == libtcod.KEY_KP4 or key_char == 'h':
            player_move_or_attack(1, 0)           

        elif key.vk == libtcod.KEY_KP5 or key_char == '.':
            player_rest
 
        elif key.vk == libtcod.KEY_KP6 or key_char == 'l':
            player_move_or_attack(-1, 0)
 
        elif key.vk == libtcod.KEY_KP7 or key_char == 'y':
            player_move_or_attack(1, 1)
 
        elif key.vk == libtcod.KEY_KP8 or key_char == 'k':
            player_move_or_attack(0, 1)

        elif key.vk == libtcod.KEY_KP9 or key_char == 'u':
            player_move_or_attack(-1, 1)
            
        elif key_char == 'g':
            #pick up an item
            for object in objects:  #look for an item in the player's tile
                if object.x == player.x and object.y == player.y and object.item:
                    object.item.pick_up()
                    break
 
        elif key_char == 'i':
            #show the inventory; if an item is selected, use it
            chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
            if chosen_item is not None:
                if chosen_item.use_function is not None:
                    chosen_item.use()
                if chosen_item.equip_type is not None:
                    chosen_item.equip()                
            else:
                return 'didnt-take-turn'

        elif key_char == 'e':
            #show the equipped items; if an item is selected, un-equip it
            chosen_item = equipment_menu('Press the key next to an item to remove it, or any other to cancel.\n')
            if chosen_item is not None:
                chosen_item.remove()
            else:
                return 'didnt-take-turn'
                 
        elif key_char == 'd':
            #show the inventory; if an item is selected, drop it
            chosen_item = inventory_menu('Press the key next to an item to drop it, or any other to cancel.\n')
            if chosen_item is not None:
                chosen_item.drop()

        elif key_char == 'p':
            #pray command so send the player to the prayer function for race-based prayers
            pray()
                
        elif key_char == '<':            
            #check if player is standing on up stairs and if so, generate new level, otherwise give message
            check = False
            for object in objects:
                if object.char == '<':
                    if object.x == player.x and object.y == player.y:
                       check = True
            if check: 
                generate_new_level()
                message('You climb up the stairs...', libtcod.red)
            else:
                message('There is no way up here!', libtcod.red)
                return 'didnt-take-turn'

        elif key_char == '?':            
            #help for new players!
            help_menu()
            return 'didnt-take-turn'            
            
        else:
            return 'didnt-take-turn'
 
def player_death(player):
    #the game ended!
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'
 
    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.red
 
def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message(monster.name.capitalize() + ' is dead!', libtcod.orange)
    monster.char = '%'
    monster.color = libtcod.red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()
    player.fighter.restore_piety(1)
    
def leader_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message(monster.name.capitalize() + ' is dead!', libtcod.pink)
    monster.char = '%'
    monster.color = libtcod.red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()
    create_special_item(monster.x, monster.y)
    player.fighter.restore_piety(3)

def victory_death(monster):
    message(monster.name.capitalize() + ' is dead!', libtcod.pink)
    monster.char = '%'
    monster.color = libtcod.red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()
    #end the game and print a victory message for the winning player!
    victory_screen()    
    
def create_special_item(x, y):
    rand = libtcod.random_get_int(0, 0, 3)
    while rand in special_items:
        rand = libtcod.random_get_int(0, 0, 3)
    special_items.append(rand)
    if rand == 0:
        item_component = Item(use_function=increase_health) 
        item = Object(x, y, '!', 'scintillating phial', libtcod.green, item=item_component)
    elif rand == 1:
        item_component = Item(equip_type='jewellery', evasion=TOTEM_EV)
        item = Object(x, y, '"', 'grisly totem', libtcod.red, item=item_component)    
    elif rand == 2:
        item_component = Item(equip_type='weapon', power=GLOWING_BROAD_SWORD_POWER) 
        item = Object(x, y, ')', 'glowing broad sword', libtcod.light_violet, item=item_component)    
    elif rand == 3:
        item_component = Item(equip_type='armour', defence=MITHRIL_DEFENCE, evasion=MITHRIL_EV) 
        item = Object(x, y, ']', 'mithril coat', libtcod.cyan, item=item_component)
    objects.append(item)        
 
def target_tile(max_range=None):
    #return the position of a tile left-clicked in player's FOV (optionally in a range), or (None,None) if right-clicked.
    while True:
        #render the screen. this erases the inventory and shows the names of objects under the mouse.
        render_all()
        libtcod.console_flush()
 
        key = libtcod.console_check_for_keypress()
        mouse = libtcod.mouse_get_status()  #get mouse position and click status
        (x, y) = (player.x - mouse.cx + VIEW_WIDTH / 2, player.y - mouse.cy + VIEW_HEIGHT / 2)
 
        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return (None, None)  #cancel if the player right-clicked or pressed Escape
 
        #accept the target if the player clicked in FOV, and in case a range is specified, if it's in that range
        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
            (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)
 
def target_monster(max_range=None):
    #returns a clicked monster inside FOV up to a range, or None if right-clicked
    while True:
        (x, y) = target_tile(max_range)
        if x is None:  #player cancelled
            return None
 
        #return the first clicked monster, otherwise continue looping
        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj
 
def closest_monster(max_range):
    #find closest enemy, up to a maximum range, and in the player's FOV
    closest_enemy = None
    closest_dist = max_range + 1  #start with (slightly more than) maximum range
 
    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
            #calculate distance between this object and the player
            dist = player.distance_to(object)
            if dist < closest_dist:  #it's closer, so remember it
                closest_enemy = object
                closest_dist = dist
    return closest_enemy
 
def ray_effect(x1, y1, x2, y2, color):
    #shows a ray animation as a fuzzy line between 2 tiles.
    render_all()  #first, re-render the screen (erase inventory, etc)
    libtcod.console_set_foreground_color(0, color)

    for frame in range(ANIMATION_FRAMES):
        #for each frame of the animation, start a line between the tiles
        libtcod.line_init(x1, y1, x2, y2)
        while True:  #step through all tiles in the line
            (x, y) = libtcod.line_step()
            if x is None: break
            
            #draw a tile as a random character made of little squares
            char = libtcod.random_get_int(0, libtcod.CHAR_SUBP_NW, libtcod.CHAR_SUBP_SW)
            libtcod.console_put_char(0, player.x - x + VIEW_WIDTH / 2, player.y - y + VIEW_HEIGHT / 2, char, libtcod.BKGND_NONE)
            
        libtcod.console_check_for_keypress()
        libtcod.console_flush()  #show result

def explosion_effect(cx, cy, radius, inner_color, outer_color):
    render_all()  #first, re-render the screen
    num_frames = float(ANIMATION_FRAMES)  #number of frames as a float, so dividing an int by it doesn't yield an int

    for frame in range(ANIMATION_FRAMES):
        #loop through all tiles in a square around the center. min and max make sure it doesn't go out of the map.
        for x in range(0, MAP_WIDTH):
            for y in range(0, MAP_HEIGHT):
                #only draw on visible floor tile
                if not map[x][y].blocked and libtcod.map_is_in_fov(fov_map, x, y):
                    #interpolate between inner and outer color
                    r = 0.5 * radius * frame/num_frames  #the radius expands as the animation advances
                    sqr_dist = (x - cx) ** 2 + (y - cy) ** 2  #the squared distance from tile to center
                    #alpha increases with radius (0.9*r) and decreases with distance to center. the +0.1 prevents a division by 0 at the center.
                    alpha = (0.9*r) ** 2 / (sqr_dist + 0.1)
                    color = libtcod.color_lerp(outer_color, inner_color, min(1, alpha))  #interpolate colors. also prevent alpha > 1.
                    
                    #interpolate between previous color and ground color (fade away from the center)
                    alpha = r ** 2 / (sqr_dist + 0.1)  #same as before, but with the full radius (r) instead of (0.9*r)
                    alpha = min(alpha, 4*(1 - frame/num_frames))  #impose on alpha an upper limit that decreases as the animation advances, so it fades out in the end
                    color = libtcod.color_lerp(color_light_ground, color, min(1, alpha))  #same as before
                    libtcod.console_set_back(con, player.x - x + VIEW_WIDTH / 2, player.y - y + VIEW_HEIGHT / 2, color, libtcod.BKGND_SET)  #set the tile color
                    libtcod.console_blit(con, 0, 0, VIEW_WIDTH, VIEW_HEIGHT, 0, 0, 0)
        libtcod.console_check_for_keypress()
        libtcod.console_flush()  #show result
    render_all()

def double_explosion_effect(cx1, cy1, cx2, cy2, radius, inner_color, outer_color):
    render_all()  #first, re-render the screen
    num_frames = float(ANIMATION_FRAMES)  #number of frames as a float, so dividing an int by it doesn't yield an int

    for frame in range(ANIMATION_FRAMES):
        #loop through all tiles in a square around the center. min and max make sure it doesn't go out of the map.
        for x in range(0, MAP_WIDTH):
            for y in range(0, MAP_HEIGHT):
                #only draw on visible floor tile
                if not map[x][y].blocked and libtcod.map_is_in_fov(fov_map, x, y):
                    #interpolate between inner and outer color
                    r = 0.5 * radius * frame/num_frames  #the radius expands as the animation advances
                    sqr_dist1 = (x - cx1) ** 2 + (y - cy1) ** 2  #the squared distance from tile to center
                    sqr_dist2 = (x - cx2) ** 2 + (y - cy2) ** 2  #the squared distance from tile to center
                    #alpha increases with radius (0.9*r) and decreases with distance to center. the +0.1 prevents a division by 0 at the center.
                    alpha1 = (0.9*r) ** 2 / (sqr_dist1 + 0.1)
                    alpha2 = (0.9*r) ** 2 / (sqr_dist2 + 0.1)
                    color1 = libtcod.color_lerp(outer_color, inner_color, min(1, alpha1))  #interpolate colors. also prevent alpha > 1.
                    color2 = libtcod.color_lerp(outer_color, inner_color, min(1, alpha2))  #interpolate colors. also prevent alpha > 1.
                    #interpolate between previous color and ground color (fade away from the center)
                    alpha1 = r ** 2 / (sqr_dist1 + 0.1)  #same as before, but with the full radius (r) instead of (0.9*r)
                    alpha2 = r ** 2 / (sqr_dist2 + 0.1)  #same as before, but with the full radius (r) instead of (0.9*r)
                    alpha1 = min(alpha1, 4*(1 - frame/num_frames))  #impose on alpha an upper limit that decreases as the animation advances, so it fades out in the end
                    alpha2 = min(alpha2, 4*(1 - frame/num_frames))  #impose on alpha an upper limit that decreases as the animation advances, so it fades out in the end
                    color1 = libtcod.color_lerp(color_light_ground, color1, min(1, alpha1))  #same as before
                    color2 = libtcod.color_lerp(color_light_ground, color2, min(1, alpha2))  #same as before
                    libtcod.console_set_back(con, player.x - x + VIEW_WIDTH / 2, player.y - y + VIEW_HEIGHT / 2, color1 + color2, libtcod.BKGND_SET)  #set the tile color
                    libtcod.console_blit(con, 0, 0, VIEW_WIDTH, VIEW_HEIGHT, 0, 0, 0)
        libtcod.console_check_for_keypress()
        libtcod.console_flush()  #show result
    render_all()
    
    
def cast_heal():
    #heal the player
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'
 
    message('Your wounds start to feel better!', libtcod.yellow)
    explosion_effect(player.x, player.y, 1, libtcod.light_red, libtcod.yellow)  #show effect
    player.fighter.heal(HEAL_AMOUNT)
 
def cast_restore_mana():
    #restore mana for the player
    if player.fighter.mana == player.fighter.max_mana:
        message('You are already at full mana.', libtcod.red)
        return 'cancelled'
 
    message('You feel a surge of power!', libtcod.light_violet)
    explosion_effect(player.x, player.y, 1, libtcod.magenta, libtcod.light_violet)  #show effect
    player.fighter.restore_mana(RESTORE_MANA_AMOUNT) 
 
def cast_lightning():
    if player.fighter.mana >= LIGHTNING_COST:
        player.fighter.use_mana(LIGHTNING_COST)
        #find closest enemy (inside a maximum range) and damage it
        monster = closest_monster(LIGHTNING_RANGE)
        if monster is None:  #no enemy found within maximum range
            message('No enemy is close enough to strike.', libtcod.red)
            return 'cancelled'
 
        #zap it!
        message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
            + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
        monster.fighter.take_damage(LIGHTNING_DAMAGE)
        
        #show ray effect
        ray_effect(player.x, player.y, monster.x, monster.y, libtcod.white)
    else:
        message('Not enough mana!', libtcod.red)
        return 'cancelled'

def cast_magic_missle():
    if player.fighter.mana >= MAGIC_MISSLE_COST:
        player.fighter.use_mana(MAGIC_MISSLE_COST)

        #ask the player for a target to magic missle
        message('Left-click an enemy for the magic missle, or right-click to cancel.', libtcod.light_magenta)
        monster = target_monster(MAGIC_MISSLE_RANGE)
        if monster is None: return 'cancelled'
 
        #zap it!
        message('A magic missle strikes the ' + monster.name + ' with a burst of energy! The damage is '
            + str(MAGIC_MISSLE_DAMAGE) + ' hit points.', libtcod.light_blue)
        monster.fighter.take_damage(MAGIC_MISSLE_DAMAGE)
        
        #show ray effect
        ray_effect(player.x, player.y, monster.x, monster.y, libtcod.light_magenta)
    else:
        message('Not enough mana!', libtcod.red)
        return 'cancelled'

def cast_blink():
    if player.fighter.mana >= BLINK_COST:
        player.fighter.use_mana(BLINK_COST)

        #ask the player for a target to blink to
        message('Left-click the target location, or right-click to cancel.', libtcod.light_blue)
        (x, y) = target_tile()
        if not is_blocked(x, y):
            double_explosion_effect(player.x, player.y, x, y, 3, libtcod.light_blue, libtcod.light_pink)
            player.x = x
            player.y = y
        else:
            message('Target location is blocked!', libtcod.red)
    else:
        message('Not enough mana!', libtcod.red)
        return 'cancelled'
                
def cast_fireball():
    if player.fighter.mana >= FIREBALL_COST:
        player.fighter.use_mana(FIREBALL_COST)
        #ask the player for a target tile to throw a fireball at
        message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
        (x, y) = target_tile()
        if x is None: return 'cancelled'
        message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
 
        #show an explosion
        explosion_effect(x, y, FIREBALL_RADIUS + 1, libtcod.white, libtcod.orange)
 
        for obj in objects:  #damage every fighter in range, including the player
            if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
                message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
                obj.fighter.take_damage(FIREBALL_DAMAGE)
    else:
        message('Not enough mana!', libtcod.red)
        return 'cancelled'

def cast_acid_arrow():
    if player.fighter.mana >= ACID_ARROW_COST:
        player.fighter.use_mana(ACID_ARROW_COST)
        #ask the player for a target tile to throw an acid arrow at
        message('Left-click a target tile for the acid arrow, or right-click to cancel.', libtcod.light_cyan)
        (x, y) = target_tile()
        if x is None: return 'cancelled'
        message('The acid arrow explodes, splashing everything within ' + str(ACID_ARROW_RADIUS) + ' tiles!', libtcod.light_chartreuse)
 
        #show an explosion
        explosion_effect(x, y, ACID_ARROW_RADIUS + 1, libtcod.dark_chartreuse, libtcod.light_chartreuse)
 
        for obj in objects:  #damage every fighter in range, including the player
            if obj.distance(x, y) <= ACID_ARROW_RADIUS and obj.fighter:
                message('The ' + obj.name + ' gets scalded for ' + str(ACID_ARROW_DAMAGE) + ' hit points.', libtcod.light_chartreuse)
                obj.fighter.take_damage(ACID_ARROW_DAMAGE)
    else:
        message('Not enough mana!', libtcod.red)
        return 'cancelled'
		
def cast_confuse():
    if player.fighter.mana >= CONFUSE_COST:
        player.fighter.use_mana(CONFUSE_COST)
        #ask the player for a target to confuse
        message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
        monster = target_monster(CONFUSE_RANGE)
        if monster is None: return 'cancelled'
 
        explosion_effect(monster.x, monster.y, 1, libtcod.light_green, libtcod.dark_green)  #show effect
        
        #replace the monster's AI with a "confused" one; after some turns it will restore the old AI
        old_ai = monster.ai
        monster.ai = ConfusedMonster(old_ai)
        monster.ai.owner = monster  #tell the new component who owns it
        message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)
    else:
        message('Not enough mana!', libtcod.red)
        return 'cancelled'

def increase_health():
    #increase the health max
    player.fighter.max_hp = player.fighter.max_hp + 15
    player.fighter.hp = player.fighter.max_hp
    message('The liquid heals and invigorates you!', libtcod.yellow)
    explosion_effect(player.x, player.y, 10, libtcod.light_red, libtcod.yellow)  #show effect

def pray():
    if player.name == 'orc':
        message('You call upon Gruumsh for help!', libtcod.yellow)
        orc_prayer()        
    elif player.name == 'kobold':
        message('You call upon Gaknulak for help!', libtcod.yellow)
        kobold_prayer()
    elif player.name == 'goblin':
        message('You call upon Maglubiyet for help!', libtcod.yellow)
        goblin_prayer()

def orc_prayer():
    if player.fighter.piety < 5:
        player.fighter.piety = 0
        message('Gruumsh is angered by your lack of devotion!', libtcod.red)
        message('You feel the effects of an ancient curse!', libtcod.red)
        curse(player)
        explosion_effect(player.x, player.y, 20, libtcod.black, libtcod.violet)
    elif player.fighter.status_effect == 'war_lust':
        message('Gruumsh is already aiding you!', libtcod.yellow)
    else:
        player.fighter.use_piety(5)
        message('Gruumsh is pleased by your ongoing worship!', libtcod.yellow)
        message('You become enraged and consumed with warlust!', libtcod.red)
        player.fighter.status_effect = 'war_lust'
        player.fighter.timer = libtcod.random_get_int(0, 10, 15)
        calc_stats()
        explosion_effect(player.x, player.y, 20, libtcod.dark_red, libtcod.red)

def kobold_prayer():
    if player.fighter.piety < 5:
        player.fighter.piety = 0
        message('Gaknulak is angered by your lack of devotion!', libtcod.red)
        message('You feel the effects of an ancient curse!', libtcod.red)
        curse(player)
        explosion_effect(player.x, player.y, 20, libtcod.black, libtcod.violet)        
    elif player.fighter.status_effect == 'invisible':
        message('Gaknulak is already aiding you!', libtcod.yellow)
    else:
        player.fighter.use_piety(5)
        message('Gaknulak is pleased by your ongoing worship!', libtcod.yellow)
        message('You slip into the shadows to avoid detection!', libtcod.grey)
        player.fighter.status_effect = 'invisible'
        player.fighter.timer = libtcod.random_get_int(0, 10, 15)
        explosion_effect(player.x, player.y, 20, libtcod.black, libtcod.grey)        
        
def goblin_prayer():
    if player.fighter.piety < 5:
        player.fighter.piety = 0
        message('Maglubiyet is angered by your lack of devotion!', libtcod.red)
        message('You feel the effects of an ancient curse!', libtcod.red)
        curse(player)
        explosion_effect(player.x, player.y, 20, libtcod.black, libtcod.violet)
    else:
        player.fighter.use_piety(5)
        message('Maglubiyet is pleased by your ongoing worship!', libtcod.yellow)
        for object in objects: #curse them all!
            if object.ai != None and object != player:
                 if libtcod.map_is_in_fov(fov_map, object.x, object.y):
                     curse(object)
                     message(object.name.capitalize() + ' is cursed by Maglubiyet!', libtcod.light_violet)
                     explosion_effect(object.x, object.y, 2, libtcod.black, libtcod.light_violet)
        
def curse(monster):
    if monster == player:
        player.fighter.status_effect = 'cursed'
        player.fighter.timer = libtcod.random_get_int(0, 10, 30)
        calc_stats()
    else:
        if monster.fighter.max_power >= abs(CURSE_POWER_EFFECT): monster.fighter.power = monster.fighter.max_power + CURSE_POWER_EFFECT
        else: monster.fighter.power = 0
        if monster.fighter.max_defence >= abs(CURSE_DEFENCE_EFFECT): monster.fighter.defence = monster.fighter.max_defence + CURSE_DEFENCE_EFFECT
        else: monster.fighter.defence = 0
        if monster.fighter.max_evasion >= abs(CURSE_EV_EFFECT): monster.fighter.evasion = monster.fighter.max_evasion + CURSE_EV_EFFECT
        else: monster.fighter.evasion = 0
        
def prayer_cancel():        
    if player.fighter.status_effect == 'cursed': message('The effect of the curse expires.', libtcod.yellow)
    else: message('The effect of your prayer expires.', libtcod.yellow)
    player.fighter.status_effect = None
    calc_stats()
        
def player_orc():
    player.name = 'orc'
    player.color = libtcod.light_chartreuse
    player.fighter.hp = 40
    player.fighter.max_hp = 40
    player.fighter.mana = 5
    player.fighter.max_mana = 5
    player.fighter.piety = 15
    player.fighter.max_piety = 15
    player.fighter.defence = 15
    player.fighter.max_defence = 15
    player.fighter.power = 20
    player.fighter.max_power = 20
    player.fighter.evasion = 5
    player.fighter.max_evasion = 5
   
def player_kobold():
    player.name = 'kobold'
    player.color = libtcod.light_red
    player.fighter.hp = 20
    player.fighter.max_hp = 20
    player.fighter.mana = 15
    player.fighter.max_mana = 15
    player.fighter.piety = 15
    player.fighter.max_piety = 15
    player.fighter.defence = 5
    player.fighter.max_defence = 5
    player.fighter.power = 12
    player.fighter.max_power = 12
    player.fighter.evasion = 30
    player.fighter.max_evasion = 30
    

def player_goblin():
    player.name = 'goblin'
    player.color = libtcod.light_sea
    player.fighter.hp = 25
    player.fighter.max_hp = 25
    player.fighter.mana = 30
    player.fighter.max_mana = 30
    player.fighter.piety = 30
    player.fighter.max_piety = 30
    player.fighter.defence = 10
    player.fighter.max_defence = 10
    player.fighter.power = 15
    player.fighter.max_power = 15
    player.fighter.evasion = 15
    player.fighter.max_evasion = 15

def generate_new_level():
    global fov_map, objects, level
    level = level + 1
    for object in objects:
        objects.remove(object)
    objects = [player]
    libtcod.map_delete(fov_map)
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    make_map()
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].blocked, not map[x][y].block_sight) 
    fov_recompute = True
    libtcod.console_flush()
    render_all()

def help_menu():
    #create an off-screen console that represents the menu's window
    width = 42
    height = 15
    window = libtcod.console_new(width, height)
 
    #print the header, with auto-wrap
    libtcod.console_set_foreground_color(window, libtcod.white)
    libtcod.console_print_center(window, 20, 0, libtcod.BKGND_NONE, 'List of commands.')
 
    #print all the options
    libtcod.console_print_left(window, 0, 2, libtcod.BKGND_NONE, 'Arrow keys or hjkl + yubn to move.')
    libtcod.console_print_left(window, 0, 4, libtcod.BKGND_NONE, 'g: pick get items on the ground.')
    libtcod.console_print_left(window, 0, 5, libtcod.BKGND_NONE, 'i: use or equip items in inventory.')
    libtcod.console_print_left(window, 0, 6, libtcod.BKGND_NONE, 'e: look at or remove equipped items.')
    libtcod.console_print_left(window, 0, 7, libtcod.BKGND_NONE, 'd: drop items from inventory.')
    libtcod.console_print_left(window, 0, 8, libtcod.BKGND_NONE, 'p: pray to the gods for help.')    
    libtcod.console_print_left(window, 0, 9, libtcod.BKGND_NONE, '< or >: go up or down stairs.')
    libtcod.console_print_left(window, 0, 10, libtcod.BKGND_NONE, '. or num-pad 5: pass a turn.')
    libtcod.console_print_left(window, 0, 12, libtcod.BKGND_NONE, 'Alt-enter: Switch to and from full-screen.')
    libtcod.console_print_left(window, 0, 14, libtcod.BKGND_NONE, 'Use the mouse to look around and aim.')
    
 
    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
 
    #present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

def victory_screen():
    global game_state
    #end of game text
    window = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
    libtcod.console_set_foreground_color(window,libtcod.white)
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 5, libtcod.BKGND_NONE, '_,.-----.,_')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 6, libtcod.BKGND_NONE, ',-~           ~-.')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 7, libtcod.BKGND_NONE, ',^___           ___^.')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 8, libtcod.BKGND_NONE, ' ~"   ~"   .   "~   "~ ')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 9, libtcod.BKGND_NONE, 'Y  ,--._    I    _.--.  Y')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 10, libtcod.BKGND_NONE, '| Y     ~-. | ,-~     Y |')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 11, libtcod.BKGND_NONE, '| |        }:{        | |')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 12, libtcod.BKGND_NONE, 'j l       / | \       ! l')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 13, libtcod.BKGND_NONE, '.-~  (__,.--" .^. "--.,__)  ~-.')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 14, libtcod.BKGND_NONE, '(           / / | \ \           )')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 15, libtcod.BKGND_NONE, '\.____,   ~  \/"\/  ~   .____,/')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 16, libtcod.BKGND_NONE, '^.____                 ____.^')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 17, libtcod.BKGND_NONE, '| |T ~\  !   !  /~ T| |')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 18, libtcod.BKGND_NONE, '| |l   _ _ _ _ _   !| |')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 19, libtcod.BKGND_NONE, '| l \/V V V V V V\/ j |')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 20, libtcod.BKGND_NONE, 'l  \ \|_|_|_|_|_|/ /  !')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 21, libtcod.BKGND_NONE, '\  \[T T T T T TI/  /')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 22, libtcod.BKGND_NONE, '\  `^-^-^-^-^-^`   /')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 23, libtcod.BKGND_NONE, '\               /')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 24, libtcod.BKGND_NONE, '\.           ,/')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 25, libtcod.BKGND_NONE, '"^-.___,-^"')
    libtcod.console_print_center_rect(window, SCREEN_WIDTH / 2, 28, SCREEN_WIDTH - 10, 40, libtcod.BKGND_NONE, '...and with that last blow, the leader of the invading forces crumpled to the ground. The unexpected ferocity from the defenders of the caverns proved too much for the pale-skinned and weak-willed men from the surface. It was not long before they withdrew completely and kept their distance out of fear that they might be the next victim of the feared tribes which inhabited the depths.')
    libtcod.console_print_center(window, SCREEN_WIDTH / 2, 35, libtcod.BKGND_NONE, '(Thanks for playing!)')
    libtcod.console_blit(window, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
    game_state = 'victory'
    

    
#############################################
# Initialization & Main Loop
#############################################
 
libtcod.console_set_custom_font('terminal10x10_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Defender of the Deep', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(VIEW_WIDTH, VIEW_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

starting_text()
race_choice = starting_menu()
 
#create object representing the player
fighter_component = Fighter(hp=30, mana = 20, piety = 20, defence=10, power=10, evasion =10, death_function=player_death)
player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)

if race_choice == 0:
    player_orc()
elif race_choice == 1:
    player_kobold()
elif race_choice == 2:
    player_goblin()
 
#the lists and other variables where we will store player, inventory and other objects
objects = [player]
inventory = []
weapon = None
armour = None
jewellery = None
special_items = [] #to be used to store unique special items when they are generated 
 
#generate map (at this point it's not drawn to the screen)
level = 1
make_map()
 
#create the FOV map, according to the generated map
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].blocked, not map[x][y].block_sight) 
 
fov_recompute = True
game_state = 'playing'
player_action = None
 
#create the list of game messages and their colors, starts empty
game_msgs = []
 
#a warm welcoming message!
message('The time for vengeance is at hand! Butcher the invaders!', libtcod.red)
message('(If this is your first time, press "?" for instructions.)', libtcod.white)
 
while not libtcod.console_is_window_closed():
 
    #render the screen
    render_all()
 
    libtcod.console_flush()
 
    #erase all objects at their old locations, before they move
    for object in objects:
        vx = player.x - object.x + (VIEW_WIDTH / 2)
        vy = player.y - object.y + (VIEW_HEIGHT / 2)
        if vx in range(0, VIEW_WIDTH) and vy in range(0, VIEW_HEIGHT):
            object.clear()
 
    #handle keys and exit game if needed
    player_action = handle_keys()
    if player_action == 'exit':
        break
    
    #handle player status effects
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        if player.fighter.timer > 0:
            player.fighter.timer = player.fighter.timer - 1
            if player.fighter.timer == 0:
                prayer_cancel()
 
    #let monsters take their turn
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        for object in objects:
            if object.ai:
                object.ai.take_turn()