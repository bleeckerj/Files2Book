import { z } from "zod";

const mediaMetadataSchema = z.record(z.string(), z.any());

const crossPostSourceSchema = z.record(z.string(), z.any());

const mediaItemSchema = z.object({
  uri: z.string(),
  creation_timestamp: z.number(),
  media_metadata: mediaMetadataSchema,
  title: z.string(),
  cross_post_source: crossPostSourceSchema.optional(),
  dubbing_info: z.array(z.any()).optional(),
  media_variants: z.array(z.any()).optional(),
  product_tags: z.array(z.any()).optional(),
});

const postSchema = z.object({
  media: z.array(mediaItemSchema),
  title: z.string().optional(),
  creation_timestamp: z.number().optional(),
});

export const postsSchema = z.array(postSchema);