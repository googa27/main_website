"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useId, useRef, useState } from "react";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About" },
  { href: "/projects", label: "Projects" },
  { href: "/contact", label: "Contact" },
];

const Navigation = () => {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const close = () => setExpanded(false);
  const linkClassName = (href: string) =>
    `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      pathname === href
        ? "text-blue-600 bg-blue-50"
        : "text-gray-700 hover:text-blue-600 hover:bg-blue-50"
    }`;

  return (
    <nav
      aria-label="Main"
      className="bg-white shadow-sm border-b"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) close();
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && expanded) {
          event.preventDefault();
          close();
          buttonRef.current?.focus();
        }
      }}
    >
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link
            href="/"
            onClick={close}
            className="text-xl font-bold text-gray-900"
          >
            Portfolio
          </Link>

          <div className="hidden md:flex space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={close}
                aria-current={pathname === item.href ? "page" : undefined}
                className={linkClassName(item.href)}
              >
                {item.label}
              </Link>
            ))}
          </div>

          <div className="md:hidden">
            <button
              ref={buttonRef}
              type="button"
              aria-label="Navigation menu"
              aria-expanded={expanded}
              aria-controls={panelId}
              onClick={() => setExpanded((value) => !value)}
              className="rounded-md p-2 text-gray-700 hover:text-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              <svg
                aria-hidden="true"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={
                    expanded
                      ? "M6 6l12 12M6 18L18 6"
                      : "M4 6h16M4 12h16M4 18h16"
                  }
                />
              </svg>
            </button>
          </div>
        </div>
        <div id={panelId} hidden={!expanded} className="pb-4 md:hidden">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={close}
              aria-current={pathname === item.href ? "page" : undefined}
              className={linkClassName(item.href)}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
