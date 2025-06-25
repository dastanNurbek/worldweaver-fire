# Assets Management

The assets used for the different objects created in Blender are customizable.

The software is packaged with base assets that can be used as templates. 

On each kind of object there are restriction on what the asset should contain, depending on how the object is modeled internally.

Most assets are based on Blender's [Geometry Nodes](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/introduction.html).

## Buildings

There are 5 kinds of buildings: "Normal", Churches, Factories, Malls and Houses.

The first 4 are managed the same way: the footprint of the building is transformed into a 3D building with flat roof using [Buildify](https://paveloliva.gumroad.com/l/buildify).

The houses are blocks with sloped roofs (instead of just footprints) that are then decorated with [PBG](https://superhivemarket.com/products/pbg-2).

## Flood / Water

Flood and water get renderer with in house shaders based on [this tutorial](https://www.youtube.com/watch?v=0SJ-__0gK_k).

## Forests

The software creates the footprint of forests using the input data, and then the asset samples random points on the surface and places a tree on it.

The "placeholder" trees are basic models made in-house.

The "pretty" trees (used only when rendering) are done with [Coan Tree Generator](https://coan.gumroad.com/l/treegen).

## Roads

The software extracts road data, and then decorates it using a slightly modified version of [Next Street V3](https://superhivemarket.com/products/next-street). The cars added on the road are also from Next Street's assets.

Some roads are also bridges, which are decorated with [FRG](https://superhivemarket.com/products/next-street).

## Terrain

Terrain is rendered with a shader that uses landuse information.

The shader is made in-house, with free texture files from [FreePBR](https://freepbr.com/), [ambientCG](https://ambientcg.com/), [Poliigon](https://www.poliigon.com/textures/free) ...
