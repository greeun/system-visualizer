# Language Import Patterns Reference

Quick reference for Claude when analyzing ambiguous import patterns during Phase 2 architecture inference.

## JavaScript / TypeScript

```javascript
// ESM - named, default, namespace
import { foo } from './module'
import foo from './module'
import * as foo from './module'

// ESM - side-effect (no bindings)
import './module'

// CJS
const foo = require('./module')
const { bar } = require('./module')

// Dynamic (async)
const mod = await import('./module')

// Re-export
export { foo } from './module'
export * from './module'
```

**Resolution**: Relative paths (`./ ../`) resolve from the importing file's directory. Try `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, then `/index.*`. Bare specifiers (no `.`) are external packages.

## Python

```python
# Absolute
import package.module
from package.module import Class

# Relative (within package)
from . import sibling
from .sibling import func
from ..parent import something
```

**Resolution**: Absolute imports use `sys.path`. Relative imports (with dots) resolve from the current package. `__init__.py` marks directories as packages.

## Go

```go
import "fmt"                    // stdlib
import "github.com/user/repo"  // external
import "./internal/pkg"         // relative (rare)

import (
    "fmt"
    "net/http"
    "github.com/user/repo/pkg"
)
```

**Resolution**: Module path from `go.mod`. Internal packages use the module path prefix. Stdlib packages have no dots in path.

## Java

```java
import java.util.List;           // stdlib
import com.company.pkg.Class;    // third-party
import static com.company.Utils.method;  // static import
```

**Resolution**: Package path maps to directory structure. `com.company.pkg.Class` → `com/company/pkg/Class.java`.

## Rust

```rust
use std::collections::HashMap;   // stdlib
use crate::module::Type;         // current crate
use super::sibling;              // parent module

mod submodule;                   // declares submodule (submodule.rs or submodule/mod.rs)
```

**Resolution**: `crate::` is project root. `super::` is parent module. `mod` declarations create module tree from file structure.

## Common Patterns Across Languages

| Pattern | Meaning |
|---------|---------|
| Barrel/index files | Re-export from subdirectories (`index.ts`, `__init__.py`, `mod.rs`) |
| Circular imports | A→B→A - usually indicates tight coupling or need for restructuring |
| Deep relative paths | `../../../` - suggests file might be in wrong directory |
| Mixed import styles | CJS + ESM in same project - transitional codebase |
