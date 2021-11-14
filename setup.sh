#!/bin/bash

pathToScriptDir="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd )"

sed -i "s|REPLACEME|${pathToScriptDir}/wordlists|g" "${pathToScriptDir}/modules.json"

echo "Done"

