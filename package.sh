#!/usr/bin/env sh

readonly addon_name=RefoldEase
readonly root_dir=$(git rev-parse --show-toplevel)
readonly zip_name="${addon_name}_$(git branch --show-current).ankiaddon"

cd -- "$root_dir" || exit 1
rm -- "$zip_name" 2>/dev/null || true

git archive HEAD --format=zip --output "$zip_name"
(cd -- ajt_common && git archive HEAD --prefix="${PWD##*/}/" --format=zip -o "$root_dir/${PWD##*/}.zip")
zipmerge "$zip_name" ./*.zip
rm -- ./*.zip
