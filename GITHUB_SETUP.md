# 🚀 GitHub Setup Guide

## Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Create a new repository:
   - **Name:** `diffusion-pi` (or your preferred name)
   - **Description:** Embedded Diffusion Simulation System for Raspberry Pi Zero 2 W with ST7789 Display
   - **Visibility:** Public or Private (your choice)
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
3. Click **Create repository**

## Step 2: Push to GitHub

```bash
# Navigate to your project folder
cd "d:/UNI/CIE Third/PDE/Project_bonus/diffusion-pi"

# Set your GitHub username
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Add remote repository (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/diffusion-pi.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Clone on Raspberry Pi

### Option A: Using HTTPS (Recommended for public repos)

```bash
# SSH into your Raspberry Pi
ssh pi@<raspberry-pi-ip>

# Clone the repository
cd ~
git clone https://github.com/YOUR_USERNAME/diffusion-pi.git

# Navigate to the project
cd diffusion-pi

# Run the installer
chmod +x install.sh
./install.sh
```

### Option B: Using SSH (For private repos or if you have SSH keys set up)

```bash
# On Raspberry Pi, generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your.email@example.com"

# Display the public key
cat ~/.ssh/id_ed25519.pub

# Copy the output and add it to GitHub:
# GitHub → Settings → SSH and GPG keys → New SSH key

# Clone using SSH
cd ~
git clone git@github.com:YOUR_USERNAME/diffusion-pi.git
cd diffusion-pi
chmod +x install.sh
./install.sh
```

## Step 4: Future Updates

When you make changes and want to update the Raspberry Pi:

**On your development machine:**
```bash
cd "d:/UNI/CIE Third/PDE/Project_bonus/diffusion-pi"
git add .
git commit -m "Description of changes"
git push
```

**On Raspberry Pi:**
```bash
cd ~/diffusion-pi
sudo systemctl stop diffusion.service  # Stop the service
git pull  # Get latest changes
sudo systemctl start diffusion.service  # Restart the service
```

## Quick Reference

```bash
# Check status
git status

# View commit history
git log --oneline

# View remote URL
git remote -v

# Pull latest changes
git pull

# Check current branch
git branch
```

## Troubleshooting

**Authentication failed?**
- For HTTPS: Use a [Personal Access Token](https://github.com/settings/tokens) instead of password
- For SSH: Make sure your SSH key is added to GitHub

**Permission denied?**
- Make sure your GitHub username is correct
- Check if repository is private (requires authentication)

**Clone failed on Raspberry Pi?**
- Check internet connection: `ping github.com`
- Try HTTPS clone instead of SSH
- Make sure git is installed: `sudo apt install git`

---

**Ready to deploy!** 🎉
