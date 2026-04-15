"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ToursRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/trails");
  }, [router]);
  return null;
}
