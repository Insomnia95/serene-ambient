#!/bin/bash
# SERENE — deploy script
# Run this once from the serene/ folder

set -e

echo "→ Initializing git..."
git init
git add .
git commit -m "Initial commit: SERENE ambient site"

echo ""
echo "✓ Git ready."
echo ""
echo "Next steps:"
echo "  1. Create a repo on GitHub: https://github.com/new"
echo "     Name it: serene-ambient"
echo "     Keep it Public, don't add README"
echo ""
echo "  2. Then run:"
echo "     git remote add origin https://github.com/YOUR_USERNAME/serene-ambient.git"
echo "     git branch -M main"
echo "     git push -u origin main"
echo ""
echo "  3. Then go to https://vercel.com/new"
echo "     Import the serene-ambient repo → Deploy"
echo ""
echo "Done! Your site will be live at https://serene-ambient.vercel.app"
