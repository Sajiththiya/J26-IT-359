import { redirect } from "next/navigation";

// Preserve old bookmarks; analysis and results now live beside the upload.
export default function Page() {
  redirect("/#listen");
}
