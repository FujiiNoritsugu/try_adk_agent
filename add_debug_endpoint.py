#!/usr/bin/env python3
"""Script to add debug endpoint to server_http.py"""

# Add this endpoint after the /health endpoint (around line 208)
debug_endpoint = '''
@app.get("/debug")
async def debug_info():
    """Debug endpoint to check Leap Motion state"""
    debug_data = {
        "leap_available": LEAP_AVAILABLE,
        "service_connection": service.connection is not None,
        "service_listener": service.listener is not None,
    }
    
    if service.listener:
        debug_data["listener_frame_exists"] = service.listener.latest_frame is not None
        debug_data["listener_type"] = type(service.listener).__name__
        
        if service.listener.latest_frame:
            frame = service.listener.latest_frame
            debug_data["frame_type"] = type(frame).__name__
            debug_data["frame_has_hands"] = hasattr(frame, 'hands') and frame.hands is not None
            if hasattr(frame, 'hands') and frame.hands:
                debug_data["num_hands"] = len(frame.hands)
            else:
                debug_data["num_hands"] = 0
    
    # Try to get data using the service method
    try:
        frame_data = service.get_current_frame()
        debug_data["get_current_frame_result"] = frame_data is not None
        if frame_data:
            debug_data["frame_data_keys"] = list(frame_data.keys())
    except Exception as e:
        debug_data["get_current_frame_error"] = str(e)
    
    # Add timestamp
    debug_data["timestamp"] = datetime.now().isoformat()
    
    return debug_data

@app.get("/leap")
async def get_leap_simple():
    """Simplified endpoint that returns raw hand data if available"""
    if not LEAP_AVAILABLE:
        return {"error": "Leap Motion not available"}
    
    if not service.listener or not service.listener.latest_frame:
        return {"hands": []}
    
    frame = service.listener.latest_frame
    if not hasattr(frame, 'hands') or not frame.hands:
        return {"hands": []}
    
    hands_data = []
    for hand in frame.hands:
        hand_data = {
            "position": {
                "x": hand.palm.position.x,
                "y": hand.palm.position.y,
                "z": hand.palm.position.z
            },
            "velocity": (hand.palm.velocity.x**2 + hand.palm.velocity.y**2 + hand.palm.velocity.z**2) ** 0.5,
            "confidence": 1.0
        }
        hands_data.append(hand_data)
    
    return {"hands": hands_data}
'''

print("Add these debug endpoints to server_http.py after the /health endpoint:")
print(debug_endpoint)