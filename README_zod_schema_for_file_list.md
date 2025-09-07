# File List Schema

To ingest with `create_file_cards.py` using a file list, there is a schema definition that is used.

It's pretty simple.

The only required field is filepath. Without that, well..what's the point?

Typically filepath is a relative path. If that's the case, then you need to provide --input-path which will be interpreted as the **root** prepended to that filepath.

Metadata is just key-value pairs (strings, obvs.)

That Metadata is then shown in the preview area as <key>: <value>

If you precede the <key> for a metadata element with "_", the <key> will not be rendered in the text.

If the metadata is an empty string, this will add a blank line.

qr_data is transmogrified into a QR Code, that may or may not be suitable depending on the density of data that can be contained in the allocated size.



```
// Zod schema for a general metadata dictionary (string keys, string values or null)
// you must have one of filepath, path, uri
const MetadataSchema = z.record(z.string(), z.string().nullable());

const FileEntrySchema = z.object({
  filepath: z.string().optional(),
  path: z.string().optional(),
  uri: z.string().optional(),
  metadata: MetadataSchema.optional(),
  qr_data: z.string().optional()
}).refine(obj => Boolean(obj.filepath || obj.path || obj.uri), {
  message: "One of 'filepath', 'path' or 'uri' is required",
  path: ["filepath", "path", "uri"]
});

const FileListSchema = z.array(FileEntrySchema);
```