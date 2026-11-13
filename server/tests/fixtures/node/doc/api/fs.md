# File system

The `node:fs` module enables interacting with the file system in a way modeled on standard POSIX functions.

## `fsPromises.readFile(path[, options])`

Asynchronously reads the entire contents of a file.

```js
import { readFile } from 'node:fs/promises';
const contents = await readFile('./package.json', { encoding: 'utf8' });
```

## `fs.writeFile(file, data[, options], callback)`

When `file` is a filename, asynchronously writes data to the file, replacing the file if it already exists.
