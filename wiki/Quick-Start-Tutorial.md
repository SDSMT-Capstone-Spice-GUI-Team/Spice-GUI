# Quick Start Tutorial

This tutorial walks you through creating your first circuit in SDM Spice.

## Overview

In this tutorial, you will:
1. Create a simple voltage divider circuit
2. Run a DC Operating Point analysis
3. View the simulation results

## Step 1: Launch SDM Spice

```bash
python app/main.py
```

The application opens with three main areas:
- **Left**: Component Palette
- **Center**: Circuit Canvas
- **Right**: Properties Panel

## Step 2: Add Components

We'll create a voltage divider with two resistors and a voltage source.

### Add a Voltage Source

1. Find **Voltage Source** in the left palette
2. Drag it onto the canvas
3. Release to place it

### Add Resistors

1. Drag a **Resistor** from the palette
2. Place it above the voltage source
3. Drag another **Resistor** and place it below the first one

### Add Ground

1. Drag the **Ground** component
2. Place it at the bottom of your circuit

Your canvas should now have: 1 voltage source, 2 resistors, and 1 ground.

## Step 3: Connect Components with Wires

1. Click on a red terminal dot on a component
2. Click on another terminal dot to create a wire
3. The wire automatically routes around obstacles

**Connect:**
- Voltage source positive (+) to the top of the first resistor
- Bottom of first resistor to top of second resistor
- Bottom of second resistor to voltage source negative (-)
- Ground to the voltage source negative terminal

## Step 4: Set Component Values

### Edit the Voltage Source

1. Click on the voltage source to select it
2. In the Properties Panel (right side), find the **Value** field
3. Change it to `10` (for 10 volts)
4. Click **Apply**

### Edit the Resistors

1. Select the first resistor
2. Set its value to `1k` (1 kilo-ohm)
3. Click **Apply**
4. Select the second resistor
5. Set its value to `2k` (2 kilo-ohms)
6. Click **Apply**

## Step 5: Run Simulation

### Select Analysis Type

1. Go to **Analysis** menu
2. Select **DC Operating Point (.op)**

### Run the Simulation

1. Press **F5** or go to **Simulation > Run Simulation**
2. Wait for the simulation to complete

## Step 6: View Results

After the simulation completes:

- **Node voltages** appear on the canvas next to each node
- **Simulation output** appears in the panel below the canvas

### Expected Results

For a voltage divider with V=10V, R1=1kΩ, R2=2kΩ:

- Voltage at the junction between R1 and R2: **~6.67V**
- This follows the voltage divider formula: Vout = V × R2/(R1+R2) = 10 × 2k/(1k+2k) = 6.67V

## Step 7: Save Your Circuit

1. Press **Ctrl+S** or go to **File > Save**
2. Choose a location and filename
3. The circuit is saved as a JSON file

## Congratulations!

You've successfully:
- Created a circuit schematic
- Connected components with wires
- Configured component values
- Run a DC Operating Point simulation
- Interpreted the results

## Next Steps

- **Try DC Sweep**: Sweep the voltage source and observe how node voltages change
- **Try Transient Analysis**: Add a waveform source and see time-domain behavior
- **Build More Circuits**: Try RC circuits, RLC filters, or amplifiers

## Tips

- **Keyboard Shortcuts**: Press `R` to rotate selected components
- **Delete Components**: Select and press `Del`
- **Zoom**: Use mouse wheel to zoom in/out (if supported)
- **Save Often**: Press `Ctrl+S` to save your work

## See Also

- [[Components]] - Full list of available components
- [[Analysis Types]] - Detailed analysis options
- [[Keyboard Shortcuts]] - All available shortcuts
