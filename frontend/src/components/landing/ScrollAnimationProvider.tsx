"use client";

import React, { useEffect, useRef } from "react";

export function ScrollAnimationProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null);
  const progressBarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // 1. Reading progress bar at the top of the viewport
    const updateProgress = () => {
      if (!progressBarRef.current) return;
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = totalHeight > 0 ? Math.min(Math.max(window.scrollY / totalHeight, 0), 1) : 0;
      progressBarRef.current.style.transform = `scaleX(${progress})`;
    };

    window.addEventListener("scroll", updateProgress, { passive: true });
    updateProgress();

    if (prefersReducedMotion) {
      // Immediately reveal all elements without transitions
      const allElements = document.querySelectorAll("[data-reveal], [data-reveal-item]");
      allElements.forEach((el) => el.classList.add("is-revealed"));
      return () => {
        window.removeEventListener("scroll", updateProgress);
      };
    }

    // 2. Setup Stagger delays for child items inside [data-reveal-stagger]
    const staggerContainers = document.querySelectorAll<HTMLElement>("[data-reveal-stagger]");
    staggerContainers.forEach((container) => {
      const items = container.querySelectorAll<HTMLElement>("[data-reveal-item]");
      items.forEach((item, index) => {
        item.style.transitionDelay = `${index * 85}ms`;
      });
    });

    // 3. Native IntersectionObserver for buttery smooth reveals
    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-revealed");
            obs.unobserve(entry.target);
          }
        });
      },
      {
        root: null,
        rootMargin: "0px 0px -50px 0px",
        threshold: 0.08,
      }
    );

    const revealTargets = document.querySelectorAll("[data-reveal], [data-reveal-item]");
    revealTargets.forEach((target) => observer.observe(target));

    // 4. Parallax Float with requestAnimationFrame
    let rafId: number;
    const parallaxElements = document.querySelectorAll<HTMLElement>("[data-parallax-float]");

    const onScrollParallax = () => {
      const scrolled = window.scrollY;
      parallaxElements.forEach((el) => {
        const speed = parseFloat(el.getAttribute("data-parallax-speed") || "0.15");
        el.style.transform = `translate3d(0, ${scrolled * -speed}px, 0)`;
      });
    };

    const handleScrollWithRaf = () => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(onScrollParallax);
    };

    if (parallaxElements.length > 0) {
      window.addEventListener("scroll", handleScrollWithRaf, { passive: true });
    }

    return () => {
      window.removeEventListener("scroll", updateProgress);
      if (parallaxElements.length > 0) {
        window.removeEventListener("scroll", handleScrollWithRaf);
        cancelAnimationFrame(rafId);
      }
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      {/* Top Reading Progress Bar */}
      <div
        ref={progressBarRef}
        className="fixed top-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-[#FA651E] via-[#FD8A6B] to-[#FA651E] z-50 origin-left scale-x-0 pointer-events-none transition-transform duration-75 ease-out"
        aria-hidden="true"
      />
      {children}
    </div>
  );
}
