#!/bin/bash
# ת44, my own mutations of the "no lazy page in the room's entry" guard (tools/check-budget.ts, by content), in the public
# third copy (build-s1516-mut: not the served flag build, not the public build), on a full flag web build (vite, ssr, prerender):
#   a. the room component imports the checkout page statically (deep in the entry's graph, not main.tsx);
#   b. a barrel module re-exports the product page, and media.ts (in the entry) imports it.
# Each: the web build, then the budget check; the chunk names are listed to show no "Checkout-"/"Product-" chunk name
# would give it away. Every file is restored from its backup after each mutation.
cd "$(dirname "$0")/../build-s1516-mut/site"
export PATH=/opt/node22/bin:$PATH
B=../../s1516-tmp/mut; mkdir -p $B
build() { npm run build -w @hd/web > $B/mut-vite.log 2>&1 || { echo "web build failed"; tail -5 $B/mut-vite.log; }; }
budget() { npx tsx tools/check-budget.ts > $B/mut-budget.log 2>&1; local e=$?; sed "s/\x1b\[[0-9;]*m//g" $B/mut-budget.log | grep -E "lazy page|the room page entry|^FAIL" ; echo "check-budget exit $e"; }
names() { ls web/dist/assets | grep -E "^(Checkout|Product|Order|Cart|Legal|MockPay)-" | tr '\n' ' '; echo; }

echo "=== a. RoomExperience.tsx imports pages/Checkout statically"
cp web/src/components/RoomExperience.tsx $B/RoomExperience.tsx.bak
sed -i "0,/^import /s//import { Checkout as QaCheckout } from '..\/pages\/Checkout';\n(globalThis as Record<string, unknown>).__qaCheckout = QaCheckout;\nimport /" web/src/components/RoomExperience.tsx
grep -n "QaCheckout" web/src/components/RoomExperience.tsx | head -2
build; echo -n "lazy chunk names: "; names; budget
cp $B/RoomExperience.tsx.bak web/src/components/RoomExperience.tsx

echo "=== b. a barrel re-exports pages/Product; media.ts (in the entry) imports it"
cp web/src/media.ts $B/media.ts.bak
printf "export { Product } from './pages/Product';\n" > web/src/qa-barrel.ts
sed -i "1i import { Product as QaProduct } from './qa-barrel';\n(globalThis as Record<string, unknown>).__qaProduct = QaProduct;" web/src/media.ts
grep -n "QaProduct" web/src/media.ts | head -2
build; echo -n "lazy chunk names: "; names; budget
cp $B/media.ts.bak web/src/media.ts; rm -f web/src/qa-barrel.ts

echo "=== restored: the clean flag build again"
build; echo -n "lazy chunk names: "; names; budget
git diff --no-index --stat ../../build-s1516/site/web/src web/src && echo "web/src identical to the clean copy"
