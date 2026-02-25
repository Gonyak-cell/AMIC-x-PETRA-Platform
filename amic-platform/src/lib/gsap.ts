import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

// Register GSAP plugins
gsap.registerPlugin(ScrollTrigger, useGSAP);

// Respect prefers-reduced-motion
const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

function applyMotionPreference(e: MediaQueryList | MediaQueryListEvent) {
  if (e.matches) {
    gsap.globalTimeline.timeScale(1000);
    ScrollTrigger.getAll().forEach((t) => t.kill());
  } else {
    gsap.globalTimeline.timeScale(1);
  }
}

applyMotionPreference(motionQuery);
motionQuery.addEventListener("change", applyMotionPreference);

// Default ease for the whole project
gsap.defaults({ ease: "power2.out", duration: 0.5 });

export { gsap, ScrollTrigger, useGSAP };
