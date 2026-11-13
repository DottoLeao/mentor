---
title: Map.prototype.get()
slug: Web/JavaScript/Reference/Global_Objects/Map/get
---

# Map.prototype.get()

The **`get()`** method of `Map` instances returns a specified element from this map. If the value that is associated to the provided key is an object, then you will get a reference to that object and any change made to that object will effectively modify it inside the `Map` object.

## Syntax

```js
get(key)
```

## Return value

The element associated with the specified key, or `undefined` if the key can't be found in the `Map` object.

## Examples

```js
const myMap = new Map();
myMap.set("bar", "foo");
console.log(myMap.get("bar")); // "foo"
console.log(myMap.get("baz")); // undefined
```
