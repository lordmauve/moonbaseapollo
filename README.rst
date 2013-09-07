Moonbase Apollo
===============

Entry to PyWeek #17 <http://www.pyweek.org/17/>
Team: Wasabier/Idlier <http://pyweek.org/e/wasabi-idli2/>
Members: Dan Pope (@mauve), Arnav Khare (@iarnav)


Mankind have established Moonbase Apollo, on a distant moon. A few spacemen including you are assigned to setup the base and pave the way for establishing a colony.

But the task is not easy, as natural resources are rare in this remote part of the universe. For the colony to survive you have to mine the asteroids nearby and bring these natural resources back to base.

Flying amongst asteroids is not easy. But nothing is impossible. 

Finish all missions assigned to you by Moonbase Apollo, as everything depends on you.


INSTALLATION and DEPENDENCIES
-----------------------------

Dependencies can be installed using the `requirements.txt` file included in the package.  

	$ pip install -r requirements.txt

The main dependencies are:
 * Python 2.7 (required)
 * Pyglet v1.2alpha1 (required)
 * Wasabi.geom (required)
 * Lepton (recommended) - for explosions and special effects. Public version of lepton is buggy on 64-bit architectures. Use the working version included in our source package.
 * AVBin (recommended) for playing music


RUNNING THE GAME
----------------

Open a terminal window, "cd" into the game directory and run:

    $ python game.py


HOW TO PLAY:

The following input keys are used for this game:

    LEFT        rotate anti-clockwise
    RIGHT       rotate clockwise
    UP          thrust forward (in the direction of the ship)
    Z           shoot

Tractoring and Delivery:
Some missions might require you to tractor an object to a destination. To start tractoring an object, move your ship over that object, and a tractor beam will pick it up automatically.

To deliver a tractored item, move slowly close to the delivery point. Be careful not to crash, or accidentally kill your tractored object.

Cheats:

	F3			Skip to next mission
	F4			Back to previous mission
	F6			Select Cutter Ship
	F7			Select Lugger Ship
	F8			Select Clipper Ship


LICENSE
-------

Moonbase Alpha is licensed under the terms of the GNU General Public
License v3.0.

CREDITS
-------

Font is Gunship Condensed (c) 2003 Iconian Fonts - Daniel Zadorozny 
<http://www.1001freefonts.com/Gunship.php>

Message sounds are SFX by Circlerun
<http://opengameart.org/content/hi-tech-button-sound-pack-i-non-themed>

Laser and Explosion sounds are by Stephen M Cameron
<http://opengameart.org/content/action-shooter-soundset-wwvi>

Music is “Mutations” by Small Colin
<http://freemusicarchive.org/music/Small_Colin/Mutations_EP_Remix/01_-_Small_Colin_-_Original_-_Mutations_EP>
