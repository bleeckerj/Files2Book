# README_parsePosts.ts

## Overview

`parsePosts.ts` is a TypeScript module designed to parse and validate Instagram post metadata from JSON files, such as `posts.json` found in your Instagram archive. It uses the Zod library to define and enforce the schema for posts and their associated media items, ensuring that the data conforms to expected types and structure before further processing or usage in your application.

## Key Features
- Defines a robust schema for Instagram posts and media items using Zod.
- Validates JSON data against the schema, catching errors and inconsistencies early.
- Supports optional and required fields, nested objects, and arrays.
- Can be used to safely load, parse, and type-check Instagram archive data in TypeScript projects.

## Typical Usage
```typescript
import { postsSchema } from './postsSchema';
import postsJson from '../your_instagram_activity/media/posts.json';

const result = postsSchema.safeParse(postsJson);
if (!result.success) {
  console.error('Invalid posts data:', result.error);
} else {
  const posts = result.data;
  // Use posts as strongly-typed data
}
```

## Use Cases
- Validating Instagram archive data before processing or display.
- Ensuring type safety in TypeScript applications that consume social media metadata.
- Building tools for media organization, preview, or export based on Instagram post data.

## Requirements
- TypeScript
- Zod

## Documentation
See the module source code and Zod documentation for details on schema definition and validation options.
