# TacOps Survival Guide

A survival guide for [TacOps](https://modrinth.com/mod/tacops), the tactical shooter mod for Minecraft (Fabric): every
crafting recipe, where to find the materials, and how to keep your guns working.

**Read it at https://thedarkteri.github.io/tacops-guide/**

## Rebuilding

The recipes come straight from the mod's generated data, and the item icons are renders from the game. With Python and
Pillow, from this repository:

```
py tools/gen_guide.py <path to the TacOps mod project> tools
py tools/build_site.py tools .
```

What's in the next TacOps release shows as "Coming soon" until it's out: see `VERSION` and `COMING_SOON` at the top of
`tools/gen_guide.py`.
