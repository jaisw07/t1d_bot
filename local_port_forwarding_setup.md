# VS Code Local Port Forwarding Setup Guide

This guide explains how to use VS Code's built-in **Local Port Forwarding** (powered by Microsoft Dev Tunnels) to expose a local service (like a web server) to the internet.

## Prerequisites
- **VS Code** installed.
- A **GitHub** or **Microsoft** account for authentication.

## Step-by-Step Instructions

### 1. Start Your Local Service
Ensure your application or service is running locally on a specific port (e.g., `http://localhost:3000`).

### 2. Open the Ports View
1. Look for the **Ports** tab in the bottom panel (next to the Terminal and Output tabs).
2. If it's not visible, open the **Command Palette** (`Ctrl+Shift+P` or `Cmd+Shift+P`) and type:
   `Ports: Focus on Ports View`

### 3. Forward a Port
1. In the Ports view, click the **Forward a Port** button (or the `+` icon).
2. Enter the **Port Number** your service is using (e.g., `3000`).
3. Press **Enter**.
4. If prompted, sign in with your GitHub or Microsoft account.

### 4. Change Visibility to Public
By default, the forwarded port is **Private** (accessible only to you when signed in). To make it accessible to anyone on the web:
1. Locate your port in the Ports view.
2. Right-click on the **Visibility** column (or the port entry).
3. Select **Port Visibility > Public**.
4. **Warning:** Once public, anyone with the link can access your local service.

### 5. Access and Share the URL
1. Copy the URL from the **Forwarded Address** column.
2. Share this URL with others or use it to test your service over the internet.

## Stopping the Tunnel
To stop exposing your port, simply right-click the port in the Ports view and select **Unforward Port**, or click the **x** icon next to the port entry.
