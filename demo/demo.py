"""Demo pygame game using Sappho.

A very horrible and basic pygame game which
utilizes Sappho (hopefully) to the fullest and
acts as a test.

This could also serve as a template in the future.

Needs to use sprite groups.

"""

from __future__ import absolute_import
 
import random
import os.path
import sys
import pygame

DEMO_PATH = os.path.dirname(os.path.abspath(__file__))
os.chdir(DEMO_PATH)

# If being run from sappho project, make sure we use live code version of sappho
if os.path.exists(os.path.join(os.path.dirname(DEMO_PATH), "sappho")):
    sys.path.insert(0, os.path.dirname(DEMO_PATH))

from sappho import collide
from sappho.layers import SurfaceLayers
from sappho.camera import Camera, CameraCenterBehavior
from sappho.animate import AnimatedSprite
from sappho.tiles import TileMap, Tilesheet, tmx_file_to_tilemaps

import config

# init pygame
pygame.mixer.init(22100, -16, 2, 64)

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

THIP_SOUND = pygame.mixer.Sound("thip.ogg")
SMALL_EXPLODE_SOUND = pygame.mixer.Sound("smallexplode.ogg")
BIG_LASER_SOUND = pygame.mixer.Sound("crush.ogg")
LASER_SOUND = pygame.mixer.Sound("laser.wav")


class Player(object):

    def __init__(self, topleft):
        self.sprite = AnimatedSprite.from_gif(config.ANIMATED_SPRITE_PATH, mask_threshold=127)
        self.bullet_duration = 150
        self.bullet_size = (2, 2)
        self.bullet_color = BLUE
        self.bullet_list = pygame.sprite.Group()
        self.x_speed = 0
        self.y_speed = 0
        self.shoot_sound = LASER_SOUND

    def shoot(self, x_speed, y_speed):
        self.shoot_sound.play()
        bullet = Bullet(self.bullet_duration, self.bullet_color, self.sprite.rect.center, x_speed, y_speed, self.bullet_size)
        self.bullet_list.add(bullet)

    def update(self, camera, wall_collision_group, layer_size, timedelta):
        self.sprite.update(timedelta)

        if self.x_speed == 0 and self.y_speed == 0:
            return None

        # move
        new_coord = (self.x_speed + self.sprite.rect.topleft[0],
                     self.y_speed + self.sprite.rect.topleft[1])

        dummy_future_rect = self.sprite.rect.copy()
        dummy_future_rect.topleft = new_coord
        wrapped_coord = wrap_logic(dummy_future_rect, layer_size).topleft

        if wrapped_coord != new_coord:
            # we wrapped around the screen pacman style
            oldie = self.sprite.rect.topleft
            self.sprite.rect.topleft = wrapped_coord
            collided_with = collide.collides_rect_mask(self.sprite, wall_collision_group)
            if collided_with:   
                self.sprite.rect.topleft = oldie
        else:
            # we did NOT wrap around the screen
            closest_position, collided_with = collide.move_as_close_as_possible(self.sprite, new_coord, wall_collision_group)
            self.sprite.rect.topleft = closest_position

        camera.scroll_to(self.sprite.rect)

        if collided_with:
            THIP_SOUND.play()
            self.bullet_duration = 500
            self.bullet_color = RED
            self.bullet_size = (4, 4)
            self.shoot_sound = BIG_LASER_SOUND
            self.x_speed = 0
            self.y_speed = 0 
        else:
            self.bullet_duration = 150
            self.bullet_size = (2, 2)
            self.shoot_sound = LASER_SOUND
            self.bullet_color = BLUE


class Asteroid(pygame.sprite.Sprite):
    COLOR = GREEN
    SPAWN_DISTANCE_FROM_PLAYER = 35

    def __init__(self, center, size, x_speed, y_speed):
        image = pygame.Surface([size, size])
        self.rect = image.get_rect()
        self.rect.center = center
        self.image = image
        self.image.fill(self.COLOR)
        self.x_speed = x_speed
        self.y_speed = y_speed
        super(Asteroid, self).__init__()

    @classmethod
    def add_if_below_threshold(cls, player, asteroid_list, at_least_x_existing):

        if len(asteroid_list) < at_least_x_existing:
            plus_or_minus_x = random.choice([1, -1])
            new_asteroid_x = player.sprite.rect.top - (cls.SPAWN_DISTANCE_FROM_PLAYER * plus_or_minus_x)

            if new_asteroid_x > player.sprite.rect.left:
                x_speed = -1
            else:
                x_speed = 1

            plus_or_minus_y = random.choice([1, -1])
            new_asteroid_y = player.sprite.rect.left - (cls.SPAWN_DISTANCE_FROM_PLAYER * plus_or_minus_y)

            if new_asteroid_y > player.sprite.rect.top:
                y_speed = -1
            else:
                y_speed = 1

            another_asteroid = Asteroid((new_asteroid_x, new_asteroid_y), 10, x_speed, y_speed)
            asteroid_list.add(another_asteroid)

    def new_smaller_asteroid(self):
        """New x and y speed based on player coords

        """

        new_asteroid_x_speed = random.choice([1, -1])
        new_asteroid_y_speed = random.choice([1, -1])

        new_asteroid_size = self.rect.width / 2
        new_asteroid = Asteroid(self.rect.center,
                                new_asteroid_size,
                                new_asteroid_x_speed,
                                new_asteroid_y_speed)
        return new_asteroid

    def explode(self, asteroid_list):
        """Explode into as many pieces as ... size

        """

        if self.rect.width > 5:

            for i in range(int(self.rect.width / 2)):
                new_asteroid = self.new_smaller_asteroid()
                asteroid_list.add(new_asteroid)

        asteroid_list.remove(self)

    def update(self, wall_list, layer_size, asteroid_list, player_bullet_list, timedelta):
        self.rect.topleft = (self.rect.left + self.x_speed,
                             self.rect.top + self.y_speed)

        new_rect = wrap_logic(self.rect, layer_size)
        self.rect = new_rect
             
        # colliding with wall?
        collision_wall = collide.collides_rect_mask(self, wall_list)

        if collision_wall:
            self.explode(asteroid_list)


class Bullet(pygame.sprite.Sprite):

    def __init__(self, duration, color, center, x_speed, y_speed, size):
        self.image = pygame.Surface(size)
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.center = center
        self.x_speed = x_speed
        self.y_speed = y_speed
        self.current_duration = 0
        self.total_duration = duration
        super(Bullet, self).__init__()

    def update(self, wall_list, asteroid_list, player_bullet_list, timedelta):
        self.current_duration += timedelta

        if self.current_duration >= self.total_duration:
            player_bullet_list.remove(self)

        new_coord = (self.rect.left + self.x_speed,
                     self.rect.top + self.y_speed)
        collision_asteroids = collide.sprites_in_orthogonal_path(self,
                                                                 new_coord,
                                                                 asteroid_list)

        if collision_asteroids:
            SMALL_EXPLODE_SOUND.play()

            for asteroid in collision_asteroids:
                asteroid.explode(asteroid_list)

            player_bullet_list.remove(self)
             
        # colliding with wall?
        collision_wall = collide.sprites_in_orthogonal_path(self, new_coord, wall_list)

        if collision_wall:
            player_bullet_list.remove(self)
            THIP_SOUND.play()
        else:
            self.rect.topleft = new_coord


def wrap_logic(rect, layer_size):
    new_rect = rect.copy()

    if new_rect.centery > layer_size[1]:
        new_rect.centery -= layer_size[1]
    elif new_rect.centery < 0:
        new_rect.centery += layer_size[1]

    if new_rect.centerx > layer_size[0]:
        new_rect.centerx -= layer_size[0]
    elif new_rect.centerx < 0:
        new_rect.centerx += layer_size[0]

    return new_rect


# Setup #######################################################################
pygame.init()
 
# Set the width and height of the screen [width,height]
screen = pygame.display.set_mode(config.RESOLUTION)
 
# Set the caption in the title bar
pygame.display.set_caption(config.WINDOW_TITLE)
 
# Loop until the user clicks the close button.
done = False
 
# Used to manage how fast the screen updates
clock = pygame.time.Clock()
 
# Hide the mouse cursor
pygame.mouse.set_visible(0)
 
# a background animation
# will be paralax
animated_bg = AnimatedSprite.from_gif("bg.gif")

# The sprite which the player controls
player = Player(config.START_POSITION)

# Load the scene, namely the layered map. Layered maps are
# represented as a list of TileMap objects.
tilesheet = Tilesheet.from_file(config.TILESHEET_PATH, *config.START_POSITION)
tilemaps_by_layer = tmx_file_to_tilemaps(config.TMX_PATH, tilesheet)

# ... Make a list of surfaces from the tilemaps.
tilemap_surfaces = []

for tilemap_representing_layer in tilemaps_by_layer:
    tilemap_surfaces.append(tilemap_representing_layer.to_surface())

# Set up the camera
surface_size = tilemap_surfaces[0].get_size()
camera = Camera(surface_size, config.RESOLUTION, config.VIEWPORT,
                behavior=CameraCenterBehavior())

# The render layers which we draw to
layers = SurfaceLayers(camera.source_surface, len(tilemap_surfaces))

# Asteroids
asteroid_list = pygame.sprite.Group()

# Main program loop ###########################################################
while not done:

    # Process events
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            done = True
 
        # User pressed down on a key
        elif event.type == pygame.KEYDOWN:

            # Figure out if it was an arrow key. If so
            # adjust speed.
            if event.key == pygame.K_LEFT:
                player.x_speed = max([player.x_speed - 1, -config.MAX_SPEED])
            elif event.key == pygame.K_RIGHT:
                player.x_speed = min([player.x_speed + 1, config.MAX_SPEED])
            elif event.key == pygame.K_UP:
                player.y_speed = max([player.y_speed - 1, -config.MAX_SPEED])
            elif event.key == pygame.K_DOWN:
                player.y_speed = min([player.y_speed + 1, config.MAX_SPEED])
            elif event.key == pygame.K_d:
                player.shoot(6, 0)
            elif event.key == pygame.K_a:
                player.shoot(-6, 0)
            elif event.key == pygame.K_s:
                player.shoot(0, 6)
            elif event.key == pygame.K_w:
                player.shoot(0, -6)

    # Test if the player is going to collide with any other objects
    # and if not, move the player

    # Move the object according to the speed vector.
    #
    # We will be resetting player.sprite.rect.topleft
    # to old_topleft if there is a collision.
    tilemap_on_players_index = tilemaps_by_layer[config.ANIMATED_SPRITE_Z_INDEX]
    collision_group_on_player_index = tilemap_on_players_index.collision_group
    timedelta = clock.get_time()
    player.update(camera, collision_group_on_player_index, layers[0].get_size(), timedelta)
 
    # create some asteroids, hurdled t the player
    # we should make these chase the player, actually...
    Asteroid.add_if_below_threshold(player, asteroid_list, 10)

    # DRAWING/RENDER CODE

    # first let's render each tilemap on its respective surface
    for i, tilemap_layer in enumerate(tilemap_surfaces):
        layers[i].blit(animated_bg.image, camera.view_rect.topleft)
        layers[i].blit(tilemap_layer, (0, 0))


    # Finally let's render the animated sprite on some
    # arbitrary layer. In the future the TMX will set this.
    layers[config.ANIMATED_SPRITE_Z_INDEX].blit(player.sprite.image,
                                                player.sprite.rect.topleft)

    # draw asteroids
    asteroid_list.draw(layers[config.ANIMATED_SPRITE_Z_INDEX])
    # draw bullets
    player.bullet_list.draw(layers[config.ANIMATED_SPRITE_Z_INDEX])

    # ... Draw those layers!
    layers.render()
     
    # Let's get the timedelta and then send it to the appropriate things...
    camera.update_state("hahahahahah lies lies lies")
    animated_bg.update(timedelta)
    player.bullet_list.update(collision_group_on_player_index, asteroid_list, player.bullet_list, timedelta)
    asteroid_list.update(collision_group_on_player_index, layers[0].get_size(), asteroid_list, player.bullet_list, timedelta)
 
    # Go ahead and update the screen with what we've drawn.
    screen.blit(camera, (0, 0))
    pygame.display.flip()
 
    # Limit frames per second
    clock.tick(60)
 
# Close the window and quit.
pygame.quit()
