import posts from "./posts_1.json";
import { postsSchema } from "./postsSchema";

const result = postsSchema.safeParse(posts);

if (result.success) {
  // result.data is your validated data
  console.log("Valid!", result.data);
} else {
  // result.error contains validation errors
  console.error("Invalid!", result.error);
}