"""Builds the TacOps survival guide page from the mod's own recipe and advancement files, plus icons cropped from a
GUI-scale-4 inventory screenshot. Run: py gen_guide.py <project root> <scratchpad>"""
import base64
import html
import io
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(sys.argv[1])
SP = Path(sys.argv[2])

# The TacOps version that's out, and the next one. What's only in the next one is in the guide already, marked "Coming
# soon": the items in COMING_SOON, and wherever the page says {{SOON}}. On release day, set VERSION to NEXT_VERSION and
# empty COMING_SOON, and the marks go
VERSION = "1.2.0"
NEXT_VERSION = "1.3.0"
COMING_SOON = set()
SOON = f'<span class="soon" title="Coming in TacOps {NEXT_VERSION}">Coming soon</span>' if COMING_SOON else ""
# Sentences in a section's introduction about what's only in the next release: each on a line of its own, led by the
# mark, so it's clear the rest of the section is out already
SECTION_NOTES = {
    "ammo": "An ammo counter beside your hotbar shows the rounds in the gun and the magazines you have left.",
    "upkeep": "A wrench beside the ammo counter warns you once a gun is worn enough to jam.",
}
GEN = ROOT / "src/main/generated/data/tactical_shooter"
ICONS = SP / "icons"

# Vanilla ingredients: display name, swatch colour, how to get it, and roughly how many iron ingots it costs
MATERIALS = {
    "minecraft:iron_ingot": ("Iron Ingot", "#d9d9d6", "Smelt raw iron. Iron golems drop it too.", 1),
    "minecraft:iron_nugget": ("Iron Nugget", "#c4c4bf", "Put an iron ingot in a crafting grid for 9, or smelt iron tools and armour.", 1 / 9),
    "minecraft:iron_block": ("Block of Iron", "#ececea", "9 iron ingots.", 9),
    "minecraft:gunpowder": ("Gunpowder", "#595959", "Creepers, ghasts and witches drop it. Desert temple chests have it.", 0),
    "minecraft:tripwire_hook": ("Tripwire Hook", "#8c6b3f", "Craft an iron ingot, a stick and a plank (makes 2).", 0.5),
    "minecraft:copper_ingot": ("Copper Ingot", "#d4804c", "Smelt raw copper.", 0),
    "minecraft:redstone": ("Redstone Dust", "#c21d1d", "Mine redstone ore, deep underground.", 0),
    "minecraft:redstone_torch": ("Redstone Torch", "#9e1a1a", "Redstone dust and a stick.", 0),
    "minecraft:tnt": ("TNT", "#d63a2b", "5 gunpowder and 4 sand.", 0),
    "minecraft:leather": ("Leather", "#9b5a2e", "Cows, horses and llamas drop it.", 0),
    "#minecraft:wool": ("Any Wool", "#efefe9", "Shear sheep.", 0),
    "minecraft:paper": ("Paper", "#f4f3ea", "3 sugar cane (makes 3).", 0),
    "minecraft:sugar": ("Sugar", "#fbfbf8", "Sugar cane in a crafting grid.", 0),
    "minecraft:glass": ("Glass", "#cfe5ec", "Smelt sand.", 0),
    "minecraft:glass_pane": ("Glass Pane", "#b9dbe6", "6 glass (makes 16).", 0),
    "minecraft:glass_bottle": ("Glass Bottle", "#a9d0de", "3 glass (makes 3).", 0),
    "minecraft:glowstone_dust": ("Glowstone Dust", "#e9c65b", "Break glowstone in the Nether.", 0),
    "minecraft:glowstone": ("Glowstone", "#f2cd63", "Found in the Nether, or 4 glowstone dust.", 0),
    "minecraft:emerald": ("Emerald", "#2fbd5a", "Trade with villagers, or mine emerald ore in the mountains.", 0),
    "minecraft:flint": ("Flint", "#3b3b3b", "Break gravel.", 0),
    "minecraft:clay": ("Clay (block)", "#a3a9b8", "4 clay balls, found in rivers, swamps and lush caves.", 0),
    "#minecraft:coals": ("Coal or Charcoal", "#2b2b2b", "Mine coal ore, or smelt logs into charcoal.", 0),
    "minecraft:oak_log": ("Oak Log", "#6c5232", "Chop oak trees. It has to be oak.", 0),
    "#minecraft:planks": ("Any Planks", "#b8935d", "Any log in a crafting grid.", 0),
    "minecraft:smooth_stone": ("Smooth Stone", "#a7a7a5", "Smelt stone (smelt cobblestone twice).", 0),
    "minecraft:anvil": ("Anvil", "#484848", "3 blocks of iron and 4 iron ingots.", 31),
    "minecraft:blast_furnace": ("Blast Furnace", "#6f6f6f", "5 iron ingots, a furnace and 3 smooth stone.", 5),
    "minecraft:iron_bars": ("Iron Bars", "#a3a3a3", "6 iron ingots (makes 16).", 6 / 16),
    "minecraft:lightning_rod": ("Lightning Rod", "#c77b4d", "3 copper ingots.", 0),
    "minecraft:armor_stand": ("Armor Stand", "#8b6a43", "6 sticks and a smooth stone slab.", 0),
    "minecraft:hay_block": ("Hay Bale", "#c9a33a", "9 wheat.", 0),
    "minecraft:spyglass": ("Spyglass", "#b8743a", "2 copper ingots and an amethyst shard, from geodes.", 0),
}
# A tag of variants (the detonator takes any lightning rod), shown as its first
ALIASES = {"minecraft:lightning_rod"}

# What each item is and does. Facts from the mod's code; keep in step with it
ITEMS = {
    "tactical_rifle": ("Tactical Rifle", "Rifle · full-auto", [
        "30-round magazine, 45 with an Extended Magazine.",
        "6 damage a round. Built-in 3x scope when you aim.",
        "Loads from Rifle Magazines. 1200 durability."]),
    "pistol": ("Tactical Pistol", "Sidearm · semi-auto", [
        "12-round magazine, 18 with an Extended Magazine.",
        "6 damage a round, iron sights.",
        "One-handed: you can fire it with a Ballistic Shield in your other hand. 600 durability."]),
    "shotgun": ("Tactical Shotgun", "Shotgun · pump action", [
        "8 pellets a shot, 3.5 damage each. 6 shells, 9 with an Extended Magazine.",
        "Loads one shell at a time: fire or aim to stop loading and shoot what's in.",
        "Blasts open wooden doors and trapdoors within 2 blocks. 600 durability."]),
    "sniper_rifle": ("M24 Sniper Rifle", "Sniper rifle · bolt action", [
        "5-round magazine, 8 with an Extended Magazine. 16 damage a round, 24 on a headshot.",
        "8x scope, dead on when aimed and wild from the hip. Hold Sprint while scoped to hold your breath and steady the sway.",
        "Rounds drop over distance: the reticle's marks show where to aim at 100, 200 and 300 blocks.",
        "Players it's aimed at see the scope glint, from up to 256 blocks. 800 durability."]),
    "m80_zolja": ("M80 Zolja", "Rocket launcher · single shot", [
        "35 damage on a direct hit, then an explosion that blows through doors and glass.",
        "Backblast: anyone within 3 blocks behind you gets burned, and a wall right behind you hurts you.",
        "Comes loaded. Reload with a 64mm Rocket. Takes no attachments."]),
    "rifle_ammo": ("Rifle Magazine", "Ammo · Tactical Rifle", [
        "Each reload uses up one magazine. Stacks to 16."]),
    "pistol_ammo": ("Pistol Magazine", "Ammo · Tactical Pistol", [
        "Makes 2. Each reload uses up one magazine. Stacks to 16."]),
    "12gauge_ammo": ("12 Gauge Shell", "Ammo · Tactical Shotgun", [
        "Makes 4. Each shell loads one round. Stacks to 32."]),
    "sniper_ammo": ("7.62mm Sniper Magazine", "Ammo · M24 Sniper Rifle", [
        "Each reload uses up one magazine. Stacks to 16."]),
    "rocket_ammo": ("64mm Rocket", "Ammo · M80 Zolja", [
        "One rocket a reload. Stacks to 8."]),
    "suppressor": ("Suppressor", "Muzzle · rifle, pistol, sniper", [
        "Quieter shots that carry less far, no muzzle flash, 20% less recoil."]),
    "extended_mag": ("Extended Magazine", "Magazine · rifle, pistol, shotgun, sniper", [
        "50% more rounds: rifle 45, pistol 18, shotgun 9 shells, sniper 8."]),
    "red_dot_sight": ("Red Dot Sight", "Optic · rifle, pistol, shotgun", [
        "A 1.35x zoom with a red dot. On the rifle it replaces the 3x scope."]),
    "laser_sight": ("Tactical Red Laser Sight", "Underbarrel · rifle, pistol, shotgun, sniper", [
        "A visible beam out to 30 blocks, and 35% less spread from the hip."]),
    "weapon_flashlight": ("Mounted Weapon Flashlight", "Underbarrel · rifle, pistol, shotgun, sniper", [
        "Press F to switch it on. Lights up to 24 blocks ahead.",
        "Dazzles players within 6 blocks looking into it and blinds mobs for a moment."]),
    "full_choke": ("Full Choke", "Muzzle · shotgun only", [
        "Pellet spread 40% tighter, for reaching further."]),
    "breaching_choke": ("Breaching Choke", "Muzzle · shotgun only", [
        "Breaches from 3.5 blocks away, and also fences, fence gates and glass.",
        "Knocks targets back harder up close."]),
    "gun_cleaning_kit": ("Gun Cleaning Kit", "Upkeep", [
        "4 uses. Each restores half a gun's durability and clears a jam.",
        "Craft it together with the gun, or hold it in your offhand and sneak + right-click with the gun."]),
    "gunsmith_workbench": ("Gunsmith Workbench", "Upkeep · block", [
        "Place it and lay a gun on it to swap attachments, compare stats and clean it with a kit.",
        "The gun stays on the bench for everyone to see until someone takes it."]),
    "target_dummy": ("Target Dummy", "Training", [
        "Shows the damage and distance of every hit, and your damage per second.",
        "Never dies and heals 2 seconds after the last hit. Hit it while sneaking to pick it up."]),
    "plate_carrier": ("Plate Carrier", "Chest armour", [
        "Its plates stop 60% of gunshot damage to the upper body, and of grenade and claymore shrapnel.",
        "Head and leg hits miss the plates. 500 durability, repair with iron ingots."]),
    "nvg_helmet": ("Night Vision Goggles", "Helmet", [
        "Press N to switch them on: night vision that never runs out. Repair with iron ingots.",
        "Mount them on a Ballistic Helmet to wear both."]),
    "ballistic_helmet": ("Ballistic Helmet", "Helmet", [
        "Its shell stops half the damage of gunshots to the head: a sniper headshot leaves you standing.",
        "Against anything else, as good as an iron helmet. 400 durability, repair with iron ingots.",
        "Mount Night Vision Goggles on it: craft the two together, or right-click the goggles onto it. N switches them on as usual."]),
    "ballistic_shield": ("Ballistic Shield", "Shield", [
        "Hold right click to raise it: stops gunfire, shrapnel and projectiles from the front.",
        "Keep it in your offhand and fire a pistol past it. Two-handed guns can't fire with it.",
        "750 durability, one per hit. Repair with iron ingots."]),
    "stimpack": ("Adrenaline Stimpack", "Healing", [
        "Hold right click to inject: heals 4 hearts, Speed II and Resistance I for 12 seconds.",
        "Clears flashbang blindness and flashlight glare. Stacks to 4."]),
    "frag_grenade": ("Frag Grenade", "Grenade", [
        "Hold right click to pull the pin and start the 3 second fuse, release to throw. Sneak to lob it.",
        "Hold on to cook it. Hold the whole 3 seconds and it goes off in your hand.",
        "Explodes with shrapnel. Stacks to 16."]),
    "smoke_grenade": ("Smoke Grenade", "Grenade", [
        "A 15 second smoke cloud about 6 blocks across that flows round corners and through doors.",
        "Anyone inside is hidden from mobs."]),
    "flashbang": ("Flashbang", "Grenade", [
        "Blinds and slows everything within 12 blocks that can see the flash. Mobs lose their target."]),
    "claymore": ("M18 Claymore", "Mine", [
        "Place it facing the way you look. It arms after a couple of seconds.",
        "Goes off when a hostile mob or another player walks into the 60° cone up to 5 blocks in front.",
        "Sneak + right-click with an empty hand or shears to defuse it. Breaking it any other way sets it off."]),
    "c4_charge": ("C4 Charge", "Explosive", [
        "Right-click a block, door or mob to stick it on. You need a Remote Detonator in your inventory: the charge links to it."]),
    "remote_detonator": ("Remote Detonator", "Explosive", [
        "Right-click to set off every charge linked to it within 128 blocks."]),
}

SECTIONS = [
    ("weapons", "Weapons", "Every gun comes with a full magazine when you craft it.",
     ["tactical_rifle", "pistol", "shotgun", "sniper_rifle", "m80_zolja"]),
    ("ammo", "Ammo", "Press R to reload, or pull the trigger on an empty gun. A reload uses up one magazine however many rounds were left, so don't top up after a couple of shots.",
     ["rifle_ammo", "pistol_ammo", "12gauge_ammo", "sniper_ammo", "rocket_ammo"]),
    ("attachments", None, None,
     ["suppressor", "extended_mag", "red_dot_sight", "laser_sight", "weapon_flashlight", "full_choke", "breaching_choke"]),
    ("gear", "Gear", "Armour, the shield and healing.",
     ["plate_carrier", "ballistic_helmet", "nvg_helmet", "ballistic_shield", "stimpack"]),
    ("explosives", "Explosives", "Grenades, mines and remote charges.",
     ["frag_grenade", "smoke_grenade", "flashbang", "claymore", "c4_charge", "remote_detonator"]),
    ("upkeep", None, None,
     ["gun_cleaning_kit", "gunsmith_workbench", "target_dummy"]),
]

ORDER = [
    ("Early", "First iron, leather and some creeper gunpowder", ["pistol", "pistol_ammo", "frag_grenade", "plate_carrier", "ballistic_helmet", "suppressor"]),
    ("Middle", "A steady iron supply, redstone and copper", ["tactical_rifle", "rifle_ammo", "shotgun", "12gauge_ammo", "red_dot_sight", "laser_sight", "gun_cleaning_kit", "smoke_grenade", "claymore"]),
    ("Late", "Iron blocks, TNT, the Nether, an emerald and a spyglass", ["gunsmith_workbench", "ballistic_shield", "sniper_rifle", "sniper_ammo", "m80_zolja", "rocket_ammo", "nvg_helmet", "stimpack", "flashbang", "weapon_flashlight", "c4_charge", "remote_detonator"]),
]


def icon_uri(item_id):
    im = Image.open(ICONS / f"{item_id}.png").convert("RGBA")
    if item_id == "claymore":
        # It draws small in the inventory; trim and blow it up so it reads beside the others
        im = im.crop(im.getbbox())
        im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
        canvas = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        canvas.alpha_composite(im, ((64 - im.width) // 2, (64 - im.height) // 2))
        im = canvas
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def ingredient_key(value):
    if isinstance(value, list):
        return value[0]
    return value


def text_on(hex_colour):
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return "#111" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#fff"


def load_recipe(item_id):
    return json.loads((GEN / "recipe" / f"{item_id}.json").read_text())


def load_unlock(item_id):
    path = next((GEN / "advancement/recipes").rglob(f"{item_id}.json"))
    crit = json.loads(path.read_text())["criteria"]
    names = []
    for key, c in crit.items():
        if key == "has_the_recipe":
            continue
        for pred in c.get("conditions", {}).get("items", []):
            item = pred["items"]
            item = item[0] if isinstance(item, list) else item
            names.append(name_of(item))
    return names


def name_of(item):
    if item in MATERIALS:
        return MATERIALS[item][0]
    return ITEMS[item.split(":")[1]][0]


def grid_for(recipe):
    """9 cells of ingredient ids (or None), a legend of (letter, id, count) and whether it's shapeless"""
    cells = [None] * 9
    legend = {}
    if "pattern" in recipe:
        pattern = recipe["pattern"]
        h, w = len(pattern), max(len(row) for row in pattern)
        top, left = (3 - h) // 2, (3 - w) // 2
        for r, row in enumerate(pattern):
            for c, ch in enumerate(row):
                if ch == " ":
                    continue
                ing = ingredient_key(recipe["key"][ch])
                cells[(top + r) * 3 + left + c] = (ch, ing)
                legend.setdefault(ch, [ing, 0])[1] += 1
        return cells, [(k, v[0], v[1]) for k, v in legend.items()], False
    used = set()
    for i, ing in enumerate(recipe["ingredients"]):
        ing = ingredient_key(ing)
        name = MATERIALS[ing][0]
        letter = next(ch for ch in (name.replace("Any ", "") + "XYZQ").upper() if ch.isalpha() and ch not in used)
        used.add(letter)
        cells[i] = (letter, ing)
        legend[letter] = [ing, 1]
    return cells, [(k, v[0], v[1]) for k, v in legend.items()], True


def iron_cost(legend):
    return sum(MATERIALS[ing][3] * n for _, ing, n in legend)


def fmt_iron(cost):
    if cost <= 0:
        return None
    if cost < 1:
        return "under 1 iron ingot"
    rounded = round(cost * 2) / 2
    return f"{rounded:g} iron ingots" if rounded != 1 else "1 iron ingot"


def esc(s):
    return html.escape(s, quote=True)


VANILLA_ICON_FILES = {"#minecraft:wool": "white_wool", "#minecraft:planks": "oak_planks", "#minecraft:coals": "coal"}


def vanilla_class(ing):
    return "v-" + VANILLA_ICON_FILES.get(ing, ing.split(":")[1])


def png_uri(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


icons = {item: icon_uri(item) for item in ITEMS}
icon_css = "".join(f".m-{item}{{background-image:url({uri})}}" for item, uri in icons.items())
icon_css += "".join(f".{vanilla_class(ing)}{{background-image:url({png_uri(ICONS / 'vanilla' / (vanilla_class(ing)[2:] + '.png'))})}}"
                    for ing in MATERIALS)
used_in = {}


def card(item_id):
    name, kind, facts = ITEMS[item_id]
    recipe = load_recipe(item_id)
    cells, legend, shapeless = grid_for(recipe)
    count = recipe["result"].get("count", 1)
    for _, ing, _ in legend:
        used_in.setdefault(ing, []).append(item_id)
    unlock = load_unlock(item_id)
    iron = fmt_iron(iron_cost(legend))
    search = " ".join([name, kind] + [MATERIALS[ing][0] for _, ing, _ in legend] + (["coming soon"] if item_id in COMING_SOON else [])).lower()

    slots = []
    for cell in cells:
        if cell is None:
            slots.append('<span class="slot"></span>')
        else:
            letter, ing = cell
            label = MATERIALS[ing][0]
            slots.append(f'<span class="slot" title="{esc(label)}"><span class="ico {vanilla_class(ing)}" role="img" aria-label="{esc(label)}"></span></span>')
    legend_html = "".join(
        f'<li><span class="ico {vanilla_class(ing)}" aria-hidden="true"></span>'
        f'<span>{esc(MATERIALS[ing][0])}</span><span class="n">×{n}</span></li>'
        for letter, ing, n in legend)
    facts_html = "".join(f"<li>{esc(f)}</li>" for f in facts)
    meta = []
    if shapeless:
        meta.append('<span class="tag">Shapeless: any layout</span>')
    if iron:
        meta.append(f'<span class="tag">≈ {iron}</span>')
    count_html = f'<span class="count">{count}</span>' if count > 1 else ""
    unlock_html = " or ".join(esc(u) for u in unlock)
    return f'''
<article class="card" id="item-{item_id}" data-search="{esc(search)}">
  <header class="card-head">
    <span class="ico icon m-{item_id}" aria-hidden="true"></span>
    <div><h3>{esc(name)}{SOON if item_id in COMING_SOON else ""}</h3><p class="kind">{esc(kind)}</p></div>
  </header>
  <div class="bench" role="img" aria-label="Crafting recipe for {esc(name)}">
    <div class="grid">{"".join(slots)}</div>
    <span class="arrow" aria-hidden="true"></span>
    <span class="slot result"><span class="ico m-{item_id}" aria-hidden="true"></span>{count_html}</span>
  </div>
  <ul class="legend">{legend_html}</ul>
  <div class="meta">{"".join(meta)}</div>
  <ul class="facts">{facts_html}</ul>
  <p class="unlock">In your recipe book once you have: {unlock_html}</p>
</article>'''


def chip(item_id):
    return f'<a class="chipl" href="#item-{item_id}"><span class="ico m-{item_id}" aria-hidden="true"></span>{esc(ITEMS[item_id][0])}{SOON if item_id in COMING_SOON else ""}</a>'


sections_html = []
for sid, title, intro, items in SECTIONS:
    cards = "".join(card(i) for i in items)
    if sid == "attachments":
        head = '''
  <div class="sec-head">
    <h2>Attachments</h2>
    <p>Each gun has four slots: muzzle, magazine, optic and underbarrel, one attachment in each. The laser and the flashlight share the underbarrel slot, and the suppressor and the chokes share the muzzle.</p>
  </div>
  <div class="howto">
    <div><h4>Crafting grid</h4><p>Put the gun and the attachment in any crafting grid.</p></div>
    <div><h4>Inventory</h4><p>Pick up the attachment and right-click it onto the gun. Right-click the gun with an empty hand to take the last one off.</p></div>
    <div><h4>Gunsmith Workbench</h4><p>Lay the gun on the bench to fit and remove attachments and see the stats change.</p></div>
  </div>
  <div class="tablewrap compatwrap">
    <table class="compat">
      <thead><tr><th scope="col">Gun</th><th scope="col">Suppressor</th><th scope="col">Extended Mag</th><th scope="col">Red Dot</th><th scope="col">Laser or Flashlight</th><th scope="col">Chokes</th></tr></thead>
      <tbody>
        <tr><th scope="row">Tactical Rifle</th><td class="y">Yes</td><td class="y">Yes</td><td class="y">Yes</td><td class="y">Yes</td><td class="n">No</td></tr>
        <tr><th scope="row">Tactical Pistol</th><td class="y">Yes</td><td class="y">Yes</td><td class="y">Yes</td><td class="y">Yes</td><td class="n">No</td></tr>
        <tr><th scope="row">Tactical Shotgun</th><td class="n">No</td><td class="y">Yes</td><td class="y">Yes</td><td class="y">Yes</td><td class="y">Yes</td></tr>
        <tr><th scope="row">M24 Sniper Rifle{{SOON}}</th><td class="y">Yes</td><td class="y">Yes</td><td class="n">No (has its scope)</td><td class="y">Yes</td><td class="n">No</td></tr>
        <tr><th scope="row">M80 Zolja</th><td class="n">No</td><td class="n">No</td><td class="n">No</td><td class="n">No</td><td class="n">No</td></tr>
      </tbody>
    </table>
  </div>'''
    elif sid == "upkeep":
        head = '''
  <div class="sec-head">
    <h2>Upkeep and training</h2>
    <p>Every shot costs a gun one point of durability. Guns never break, but under 20% durability each pull of the trigger has a 5% chance to jam. Press R to rack the slide and clear a jam; it uses no ammo. A Gun Cleaning Kit puts the durability back.</p>
  </div>'''
    else:
        head = f'''
  <div class="sec-head">
    <h2>{esc(title)}</h2>
    <p>{esc(intro)}</p>
  </div>'''
    if sid in SECTION_NOTES:
        head = head.replace("\n  </div>", f'\n    <p class="upcoming">{SOON}{esc(SECTION_NOTES[sid])}</p>\n  </div>', 1)
    sections_html.append(f'<section class="sec" id="{sid}">{head}<div class="cards">{cards}</div></section>')

order_html = "".join(
    f'<div class="stage"><h3>{esc(stage)}</h3><p>{esc(need)}</p><div class="chips">{"".join(chip(i) for i in items)}</div></div>'
    for stage, need, items in ORDER)

material_rows = []
for ing, (label, colour, how, _) in sorted(MATERIALS.items(), key=lambda kv: (-len(used_in.get(kv[0], [])), kv[1][0])):
    items = used_in.get(ing, [])
    if not items:
        continue
    links = ", ".join(f'<a href="#item-{i}">{esc(ITEMS[i][0])}</a>' for i in items)
    material_rows.append(
        f'<tr data-search="{esc((label + " " + " ".join(ITEMS[i][0] for i in items)).lower())}"><th scope="row"><span class="ico {vanilla_class(ing)}" aria-hidden="true"></span>{esc(label)}</th>'
        f'<td>{esc(how)}</td><td>{links}</td></tr>')

template = (SP / "guide_template.html").read_text(encoding="utf-8")
page = (template
        .replace("{{ORDER}}", order_html)
        .replace("{{SECTIONS}}", "\n".join(sections_html))
        .replace("{{MATERIALS}}", "\n".join(material_rows))
        .replace("{{HERO_ICONS_SLOTS}}", "".join(f'<span class="slot"><span class="ico m-{i}"></span></span>' for i in ["tactical_rifle", "pistol", "shotgun", "sniper_rifle", "m80_zolja"]))
        .replace("{{ICON_CSS}}", icon_css)
        .replace("{{VERSION}}", VERSION)
        .replace("{{SOON}}", SOON))
out = SP / "tacops-survival-guide.html"
out.write_text(page, encoding="utf-8", newline="\n")
print("wrote", out, len(page) // 1024, "KB")
