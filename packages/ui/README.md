# UI foundation

The shared design tokens and responsive rules live in `apps/web/app/globals.css`. Accessible shadcn-style Button, Card, and Input primitives live in `apps/web/components/ui`, configured by `apps/web/components.json` and composed with Radix Slot, class-variance-authority, and Tailwind.

Use the existing primitives, visible labels, keyboard focus indicators, reduced-motion support, and the English/Hindi/Bengali dictionaries. Keep measurement values and medicine names unchanged. Do not introduce fake clinical data to populate empty states. Keep all medical disclaimers and unavailable-state boundaries visible.
