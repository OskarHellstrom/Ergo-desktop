import cv2

def list_ports():
    """
    Test the ports and returns a tuple with the available ports and the ones that are working.
    """
    non_working_ports = []
    dev_port = 0
    working_ports = []
    available_ports = []
    print("Checking camera ports...")
    while len(non_working_ports) < 6: # Stop after 6 consecutive failed attempts to find a new camera
        camera = cv2.VideoCapture(dev_port)
        if not camera.isOpened():
            non_working_ports.append(dev_port)
            # print(f"Port {dev_port} is not working or not available.")
        else:
            is_reading, img = camera.read()
            w = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            h = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if is_reading:
                print(f"Port {dev_port} is working and reads images ({int(w)}x{int(h)})")
                working_ports.append(dev_port)
            else:
                print(f"Port {dev_port} for camera (index {dev_port}) is present but does not read frames.")
                available_ports.append(dev_port) # Still, it opened
            camera.release()
        dev_port +=1
        if dev_port > 20 and not working_ports: # Don't scan too many if none found early
            print("Scanned up to 20 ports, stopping as no initial working ports found.")
            break
    return available_ports, working_ports, non_working_ports

if __name__ == '__main__':
    print("Attempting to find working cameras using default backend...")
    available, working, non_working = list_ports()
    print(f"\n--- Default Backend Summary ---")
    print(f"Potentially available (opened but no frame): {available}")
    print(f"Confirmed working (opened and read frame): {working}")
    # print(f"Confirmed non-working/unavailable: {non_working}")

    if not working:
        print("\nNo working camera found by index with default backend. Trying with specific backends if available.")
        
        backends_to_try = []
        if hasattr(cv2, 'CAP_V4L2'): backends_to_try.append(cv2.CAP_V4L2)
        if hasattr(cv2, 'CAP_GSTREAMER'): backends_to_try.append(cv2.CAP_GSTREAMER)
        if hasattr(cv2, 'CAP_FFMPEG'): backends_to_try.append(cv2.CAP_FFMPEG)
        if hasattr(cv2, 'CAP_MSMF'): backends_to_try.append(cv2.CAP_MSMF) # For Windows
        if hasattr(cv2, 'CAP_AVFOUNDATION'): backends_to_try.append(cv2.CAP_AVFOUNDATION) # For macOS

        found_with_specific_backend = False
        for backend_name, backend_val in [('V4L2', cv2.CAP_V4L2 if hasattr(cv2,'CAP_V4L2') else -1),
                                        ('GSTREAMER', cv2.CAP_GSTREAMER if hasattr(cv2,'CAP_GSTREAMER') else -1),
                                        ('FFMPEG', cv2.CAP_FFMPEG if hasattr(cv2,'CAP_FFMPEG') else -1),
                                        ('MSMF', cv2.CAP_MSMF if hasattr(cv2,'CAP_MSMF') else -1),
                                        ('AVFOUNDATION', cv2.CAP_AVFOUNDATION if hasattr(cv2,'CAP_AVFOUNDATION') else -1)]:
            if backend_val == -1: continue # Skip if backend enum not present

            print(f"\nAttempting with backend: {backend_name} ({backend_val})")
            for i in range(5): # Try first 5 indices with this backend
                try:
                    # print(f"Trying index {i} with backend {backend_name}...")
                    cap = cv2.VideoCapture(i, backend_val)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret:
                            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            print(f"SUCCESS: Camera index {i} ({w}x{h}) opened with backend {backend_name}!")
                            # cv2.imshow(f'Camera {i} - Backend {backend_name}', frame)
                            # cv2.waitKey(1000) # Show for 1 sec
                            cap.release()
                            # cv2.destroyAllWindows()
                            working.append(i) # Add to working list
                            found_with_specific_backend = True
                            break 
                        else:
                            # print(f"Opened index {i} with backend {backend_name}, but failed to read frame.")
                            cap.release()
                    # else:
                        # print(f"Failed to open index {i} with backend {backend_name}.")
                except Exception as e:
                    print(f"Error trying index {i} with backend {backend_name}: {e}")
            if found_with_specific_backend:
                 break # Found a working combination, no need to test other backends

    if working:
        print(f"\nTrying to display feed from the first confirmed working camera: index {working[0]}")
        # If multiple backends found a camera, this will use the first one added to 'working'
        # You might need to be more specific if testing a particular backend's success
        cap = cv2.VideoCapture(working[0]) 
        if not cap.isOpened():
            print(f"Error: Could not open camera index {working[0]} for display even though it was listed as working.")
        else:
            print("Displaying camera feed. Press 'q' to quit.")
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Error: Can't receive frame (stream end?). Exiting ...")
                    break
                cv2.imshow(f'Camera Test - Index {working[0]}', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            cap.release()
            cv2.destroyAllWindows()
    else:
        print("\nNo working camera found with any tested backend or index.")
        print("Please check camera connections, permissions, and ensure no other application is using the camera.") 