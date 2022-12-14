from LevelGen import *
from Monsters import *
from CommonContent import *
from Level import *
import sys, random

curr_module = sys.modules[__name__]

class MordredRiftBeam(SimpleRangedAttack):

    def __init__(self, spells):
        self.spells = spells
        SimpleRangedAttack.__init__(self, name="Rift Beam", damage=2, damage_type=None, range=16, beam=True, melt=True)
        self.description = "Deals 3 random damage types in a beam; melts walls. Switches to a random spell after casting."

    def get_stat(self, attr, base=None):
        if attr == "radius":
            return 0
        return SimpleRangedAttack.get_stat(self, attr, base)

    def hit(self, x, y):
        damage = self.get_stat("damage")
        for _ in range(3):
            self.caster.level.deal_damage(x, y, damage, random.choice([Tags.Holy, Tags.Dark, Tags.Poison, Tags.Lightning, Tags.Physical, Tags.Arcane, Tags.Fire, Tags.Ice]), self)

    def cast(self, x, y):
        yield from SimpleRangedAttack.cast(self, x, y)
        self.caster.spells.remove(self)
        self.caster.spells.append(random.choice(self.spells))

class MordredRiftBlast(SimpleRangedAttack):

    def __init__(self, spells):
        self.spells = spells
        SimpleRangedAttack.__init__(self, name="Rift Blast", damage=4, damage_type=None, range=10, radius=2)
        self.description = "Deals 3 random damage types. Switches to a random spell after casting."
        self.effect = [Tags.Holy, Tags.Dark, Tags.Poison, Tags.Lightning, Tags.Physical, Tags.Arcane, Tags.Fire, Tags.Ice]
    
    def hit(self, x, y):
        damage = self.get_stat("damage")
        for _ in range(3):
            self.caster.level.deal_damage(x, y, damage, random.choice(self.effect), self)

    def cast(self, x, y):
        yield from SimpleRangedAttack.cast(self, x, y)
        self.caster.spells.remove(self)
        self.caster.spells.append(random.choice(self.spells))

class MordredRiftWave(BreathWeapon):

    def __init__(self, spells):
        self.spells = spells
        BreathWeapon.__init__(self)
        self.damage_type = None
        self.damage = 3
        self.range = 12
        self.cool_down = 0
        self.name = "Rift Wave"
        self.description = "Deals 3 random damage types in a cone. Switches to a random spell after casting."

    def per_square_effect(self, x, y):
        damage = self.get_stat("damage")
        for _ in range(3):
            self.caster.level.deal_damage(x, y, damage, random.choice([Tags.Holy, Tags.Dark, Tags.Poison, Tags.Lightning, Tags.Physical, Tags.Arcane, Tags.Fire, Tags.Ice]), self)

    def cast(self, x, y):
        yield from BreathWeapon.cast(self, x, y)
        self.caster.spells.remove(self)
        self.caster.spells.append(random.choice(self.spells))

class MordredRiftWizardry(Spell):

    def on_init(self):
        self.name = "Rift Wizardry"
        if "mods.BugsAndScams.NoMoreScams" in sys.modules:
            self.description = "Teleport near the Wizard and mix the current realm with another.\nFriends and foes may be left behind; Mordred, the Wizard, and minions summoned by Conjuration skills will always remain."
        else:
            self.description = "Teleport near the Wizard and mix the current realm with another.\nFriends and foes may be left behind; Mordred and the Wizard will always remain."
        self.cool_down = 13
        self.range = 0
        self.radius = 4
        self.num_exits = 0

    def cast(self, x, y):

        player = [unit for unit in self.caster.level.units if unit.is_player_controlled][0]
        targets = [p for p in self.caster.level.get_points_in_ball(player.x, player.y, self.get_stat("radius")*2) if not self.caster.level.get_unit_at(p.x, p.y)]
        if targets:
            target = random.choice(targets)
            self.caster.level.make_floor(target.x, target.y)
            self.caster.level.act_move(self.caster, target.x, target.y, teleport=True)

        gen_params = self.caster.level.gen_params.make_child_generator(difficulty=LAST_LEVEL)        
        gen_params.num_exits = self.num_exits
        gen_params.num_monsters = 100
        gen_params.num_generators = 36
        change_last_level(gen_params, extra_enemy_types=1, num_bosses=12, add_mordred=False)
        new_level = gen_params.make_level()

        # For the new level, pick some swaths of it.
        # For each tile in that swath, transport the tile and its contents to the new level
        # For units, remove then add them to make event subscriptions work...?
        chance = random.random() * .5 + .1
        targets = []

        num_portals = len(list(t for t in self.caster.level.iter_tiles() if isinstance(t.prop, Portal)))

        for point in new_level.get_points_in_ball(self.caster.x, self.caster.y, self.get_stat("radius")):
            if random.random() > chance:
                if isinstance(self.caster.level.tiles[point.x][point.y].prop, Portal):
                    if num_portals <= 1:
                        continue
                    else:
                        num_portals -= 1
                targets.append((point.x, point.y))
        random.shuffle(targets)

        for i, j in targets:
            
            old_unit = self.caster.level.get_unit_at(i, j)
            check = False
            if old_unit:
                check = old_unit is self.caster or old_unit.is_player_controlled or old_unit.name == "Mordred"
                if "mods.BugsAndScams.NoMoreScams" in sys.modules:
                    check = check or sys.modules["mods.BugsAndScams.NoMoreScams"].is_conj_skill_summon(old_unit)
            if check:
                continue
            elif old_unit:
                old_unit.kill(trigger_death_event=False)

            new_tile = new_level.tiles[i][j]

            calc_glyph = random.choice([True, True, False])
            if new_tile.is_chasm:
                self.caster.level.make_chasm(i, j, calc_glyph=calc_glyph)
            elif new_tile.is_floor():
                self.caster.level.make_floor(i, j, calc_glyph=calc_glyph)
            else:
                self.caster.level.make_wall(i, j, calc_glyph=calc_glyph)
            
            cur_tile = self.caster.level.tiles[i][j]                
            cur_tile.tileset = new_tile.tileset
            cur_tile.water = new_tile.water
            cur_tile.sprites = None

            unit = new_tile.unit
            if unit:
                new_level.remove_obj(unit)
            if unit and not cur_tile.unit:
                self.caster.level.add_obj(unit, i, j)

            prop = new_tile.prop
            if prop:
                old_prop = cur_tile.prop
                if old_prop:
                    self.caster.level.remove_prop(old_prop)
                self.caster.level.add_prop(prop, i, j)

            # Remove props from chasms and walls
            if cur_tile.prop and not cur_tile.is_floor():
                self.caster.level.remove_prop(cur_tile.prop)

            self.caster.level.show_effect(i, j, Tags.Translocation)
            if random.random() < .25:
                yield
        yield

        self.caster.level.gen_params.ensure_connectivity()
        self.caster.level.gen_params.ensure_connectivity(chasm=True)

class MordredReincarnationBuff(ReincarnationBuff):
    def __init__(self, lives=1):
        ReincarnationBuff.__init__(self, lives=lives)
        self.color = Color(216, 27, 96)
    def respawn(self):
        for attr in ["damage", "range", "radius"]:
            self.owner.global_bonuses[attr] += 1
        self.owner.level.queue_spell(ReincarnationBuff.respawn(self))
        yield
    def get_tooltip(self):
        return "Reincarnates when killed (%d times); +1 damage, range, and radius per life lost." % self.lives

def MordredOverhauled():
    unit = Unit()
    unit.name = "Mordred"
    unit.sprite.color = Color(255, 50, 150)
    unit.sprite.char = 'M'

    unit.shields = 7
    unit.gets_clarity = True
    unit.is_final_boss = True

    spells = []
    spells.append(MordredRiftBeam(spells))
    spells.append(MordredRiftBlast(spells))
    spells.append(MordredRiftWave(spells))
    for spell in spells:
        spell.caster = unit
        spell.owner = unit
    unit.spells = [MordredRiftWizardry(), random.choice(spells)]
    
    unit.buffs.append(MordredReincarnationBuff(4))

    unit.max_hp = 697
    unit.resists[Tags.Dark] = 50
    unit.resists[Tags.Poison] = 0
    return unit

def change_last_level(self, extra_enemy_types=1, num_bosses=3, add_mordred=True):

    difficulty = LAST_LEVEL

    spawns = []

    if 'forcespawn' in sys.argv:
        forcedspawn_name = sys.argv[sys.argv.index('forcespawn') + 1]
        forced_spawn_options = [(spawn, cost) for (spawn, cost) in spawn_options if forcedspawn_name.lower() in spawn.__name__.lower()]
        assert(len(forced_spawn_options) > 0)
        spawns = forced_spawn_options
    else:
        min_level = 8
        max_level = 9

        # force 1 higher level spawn
        max_level_options = [(s, l) for s, l in spawn_options if (l == max_level) or (l == max_level - 1)]
        spawns.append(self.random.choice(max_level_options))

        # generate the rest randomly
        other_spawn_options = [(s, l) for s, l, in spawn_options if l >= min_level and l <= max_level and (s, l) not in spawns]
        for _ in range(extra_enemy_types):
            if not other_spawn_options:
                break
            cur_option = self.random.choice(other_spawn_options)
            spawns.append(cur_option)
            other_spawn_options.remove(cur_option)

    self.spawn_options = spawns
    examples = [spawn_option[0]().name for spawn_option in self.spawn_options]

    self.bosses = []
    num_boss_spawns = num_bosses

    # for debugging
    if 'forcevariant' in sys.argv:
        num_boss_spawns = 1

    for i in range(num_boss_spawns):

        spawn_type = self.random.choice(self.spawn_options)
        roll_result = roll_variant(spawn_type[0], self.random)
        if not roll_result:
            roll_result = self.get_elites(difficulty)

        roll_result = [unit for unit in roll_result if unit.name not in examples]
        if roll_result:
            self.bosses.extend(roll_result)

    num_uniques = num_bosses

    if 'forcerare' in sys.argv:
        num_uniques = 1

    for i in range(num_uniques):
        tags = set()
        
        for o in self.spawn_options:
            for t in o[0]().tags:
                tags.add(t)

        spawns = roll_rare_spawn(difficulty, tags, prng=self.random)
        spawns = [unit for unit in spawns if unit.name not in examples]
        if not spawns:
            continue
        self.bosses.extend(spawns)
    
    if add_mordred:
        self.bosses.append(MordredOverhauled())

def modify_class(cls):

    if cls is LevelGenerator:

        old_init = LevelGenerator.__init__

        def __init__(self, difficulty, game=None, seed=None):
            old_init(self, difficulty, game, seed)
            if difficulty == LAST_LEVEL - 1:
                self.num_exits = self.random.choice([2, 2, 3, 3, 3, 3, 4])
            if difficulty != LAST_LEVEL:
                return

            self.num_exits = 0
            self.num_generators = 9

            change_last_level(self)

    for func_name, func in [(key, value) for key, value in locals().items() if callable(value)]:
        if hasattr(cls, func_name):
            setattr(cls, func_name, func)

curr_module.modify_class(LevelGenerator)