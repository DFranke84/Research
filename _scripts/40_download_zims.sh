#!/usr/bin/env bash
# Download the approved core set of Kiwix ZIM archives into E:\Research\_sources\zim.
# Resumable (curl -C -); re-run to continue. Each file is verified against Kiwix's published SHA-256.
set -u
DEST=/e/Research/_sources/zim
B=https://lb.download.kiwix.org/zim
mkdir -p "$DEST"
FILES=(
  other/zimgit-post-disaster_en_2024-05.zim
  other/zimgit-water_en_2024-08.zim
  other/zimgit-medicine_en_2024-08.zim
  other/zimgit-food-preparation_en_2025-04.zim
  other/zimgit-knots_en_2024-08.zim
  other/appropedia_en_all_maxi_2026-02.zim
  other/energypedia_en_all_maxi_2026-06.zim
  zimit/nhs.uk_en_medicines_2026-09b.zim
  other/wikem_en_all_maxi_2026-07.zim
  stack_exchange/ham.stackexchange.com_en_all_2026-08.zim
  stack_exchange/outdoors.stackexchange.com_en_all_2026-08.zim
  stack_exchange/woodworking.stackexchange.com_en_all_2026-08.zim
  stack_exchange/pets.stackexchange.com_en_all_2026-08.zim
  stack_exchange/homebrew.stackexchange.com_en_all_2026-08.zim
  stack_exchange/sustainability.stackexchange.com_en_all_2026-08.zim
  stack_exchange/crafts.stackexchange.com_en_all_2026-07.zim
  stack_exchange/lifehacks.stackexchange.com_en_all_2026-08.zim
  stack_exchange/cooking.stackexchange.com_en_all_2026-07.zim
  stack_exchange/mechanics.stackexchange.com_en_all_2026-08.zim
  stack_exchange/bicycles.stackexchange.com_en_all_2026-08.zim
  stack_exchange/gardening.stackexchange.com_en_all_2026-08.zim
  stack_exchange/diy.stackexchange.com_en_all_2026-08.zim
  zimit/medlineplus.gov_en_all_2025-01.zim
  ifixit/ifixit_en_all_2025-12.zim
  wikibooks/wikibooks_en_all_nopic_2026-04.zim
)
for f in "${FILES[@]}"; do
  name=$(basename "$f")
  if [ -f "$DEST/$name.done" ]; then echo "skip $name"; continue; fi
  echo "$(date +%H:%M) start $name"
  if curl -fsSL --retry 5 --retry-delay 10 -C - -o "$DEST/$name" "$B/$f"; then
    want=$(curl -fsL "$B/$f.sha256" | awk '{print $1}')
    got=$(sha256sum "$DEST/$name" | awk '{print $1}')
    if [ -n "$want" ] && [ "$want" != "$got" ]; then
      echo "$(date +%H:%M) CHECKSUM MISMATCH $name"; mv "$DEST/$name" "$DEST/$name.bad"
    else
      touch "$DEST/$name.done"
      echo "$(date +%H:%M) done $name $(du -h "$DEST/$name" | cut -f1) sha256=${want:+verified}"
    fi
  else
    echo "$(date +%H:%M) FAILED $name"
  fi
done
echo "all finished"
