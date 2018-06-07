import cv2
import sys
from darkflow.net.build import TFNet
import time
import matplotlib.pyplot as plt
check_value = 10
no_of_trackers = 2

if sys.platform == 'win32':
    print ('Setting windows options')
    options = {
        'model': 'cfg/yolo.cfg',
        'load': 'bin/yolov2.weights',
        'threshold': 0.3
    }
else:
    print('Setting unix options')
    options = {
        'model': 'cfg/yolo.cfg',
        'load': 'bin/yolov2.weights',
        'threshold': 0.3,
        'gpu' : 1
    }

labels = ['person','tvmonitor']
colors = {'person':(0,0,0),'tvmonitor':(0,0,255)}

tfnet = TFNet(options)


(major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')

def get_iou(bb1, bb2):
    """
    Calculate the Intersection over Union (IoU) of two bounding boxes.

    Parameters
    ----------
    bb1 : list
        The (x1, y1) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner
    bb2 : list
        The (x, y) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner

    Returns
    -------
    float
        in [0, 1]
    """

    # determine the coordinates of the intersection rectangle
    x_left = max(bb1[0], bb2[0])
    y_top = min(bb1[1], bb2[1])
    x_right = min(bb1[2], bb2[2])
    y_bottom = max(bb1[3], bb2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # The intersection of two axis-aligned bounding boxes is always an
    # axis-aligned bounding box
    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    # compute the area of both AABBs
    bb1_area = (bb1[2] - bb1[0]) * (bb1[3] - bb1[1])
    bb2_area = (bb2[2] - bb2[0]) * (bb2[3] - bb2[1])

    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = intersection_area / float(bb1_area + bb2_area - intersection_area)
    #assert iou >= 0.0
    #assert iou <= 1.0
    return iou

def get_bound_boxes(frame,old_bboxes=''):
    # TODO need to do transference from old bound boxes to the new bound boxes
    # TODO carrying over id and adding new ids

    results = tfnet.return_predict(frame)
    bboxes = []
    i = 0
    for result in  results:
        label = result['label']
        if label in labels :
            # only certain labels put bound boxes
            arr1 = (int(result['topleft']['x']), int(result['topleft']['y']),
                            int(result['bottomright']['x']), int(result['bottomright']['y']))
            arr2 = (int(result['topleft']['x']), int(result['topleft']['y']),
             int(result['bottomright']['x']) - int(result['topleft']['x']),
             int(result['bottomright']['y']) - int(result['topleft']['y']))
            bboxes.append ((i,arr1,arr2))
            i =+ i
            # format for tracking
            # p1 = (int(bbox[0]), int(bbox[1]))
            # p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))

    return bboxes

def get_match(bbox,bboxes):
    for i in range(0,len(bboxes)):
        p1 = (int(bbox[0]), int(bbox[1]), int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))

        if get_iou((p1),bboxes[i][1]) > .5:
            return i

    return -1

def run():

    # Set up tracker.
    # Instead of MIL, you can also use

    tracker_types = ['BOOSTING', 'MIL', 'KCF', 'TLD', 'MEDIANFLOW', 'GOTURN']
    tracker_type = tracker_types[1]

    trackers = []

    if int(minor_ver) < 3:
        tracker = cv2.Tracker_create(tracker_type)
    else:
        if tracker_type == 'BOOSTING':
            for i in range (0, no_of_trackers):
                tracker = cv2.TrackerBoosting_create()
                trackers.append(tracker)
        if tracker_type == 'MIL':
            for i in range (0, no_of_trackers):
                tracker = cv2.TrackerMIL_create()
                trackers.append(tracker)
        if tracker_type == 'KCF':
            for i in range (0, no_of_trackers):
                tracker = cv2.TrackerKCF_create()
                trackers.append(tracker)
        if tracker_type == 'TLD':
            for i in range (0, no_of_trackers):
                tracker = cv2.TrackerTLD_create()
                trackers.append(tracker)
        if tracker_type == 'MEDIANFLOW':
            for i in range (0, no_of_trackers):
                tracker = cv2.TrackerMedianFlow_create()
                trackers.append(tracker)
        if tracker_type == 'GOTURN':
            for i in range (0, no_of_trackers):
                tracker = cv2.TrackerGOTURN_create()
                trackers.append(tracker)


    # Read video
    video = cv2.VideoCapture("./video/TUD-Stadtmitte.mp4")

    # Exit if video not opened.
    if not video.isOpened():
        print("Could not open video")

        sys.exit()

    # Read first frame.
    ok, frame = video.read()
    if not ok:
        print('Cannot read video file')
        sys.exit()

    # Define an initial bounding box
    bbox = []

    # bbox values provided by selectROI
    #bbox = cv2.selectROI(frame, False)
    bbox.append((0,(81, 93, 91, 234)))
    bbox.append((6,(354, 77, 74, 257)))

    # bbox values provided by TF x,y , manipulated x , manipulated y
    #bbox.append((91, 97, 65, 225))
    #bbox.append((352, 70, 83, 272))



    # Initialize trackers with first frame and bounding box
    for i in range(0,no_of_trackers):
        tracker = trackers[i]
        ok = tracker.init(frame, bbox[i][1])
        trackers[i] = tracker

    counter = 0
    while True:
        # Read a new frame
        ok, frame = video.read()
        if not ok:
            break

        # Start timer
        timer = cv2.getTickCount()

        if counter % check_value == 0:
            bboxes = get_bound_boxes(frame)

        # Update tracker
        for i in range(0, no_of_trackers):
            tracker = trackers[i]
            ok, bbox1 = tracker.update(frame)
            # Draw bounding box
            if ok:
                if counter % check_value == 0 :
                    # every nth course correct
                    # and reset tracker - set new bbox
                    print('reTargetting')
                    position = get_match(bbox1, bboxes)
                    if position != -1:
                        print('matched, reseting tracker to new values in frame')
                        tracker = cv2.TrackerMIL_create()
                        ok = tracker.init(frame, bboxes[position][2])
                        trackers[i] = tracker
                        bbox1 = bboxes[position][2]
                    else:
                        print('need to reset')


                # Tracking success
                p1 = (int(bbox1[0]), int(bbox1[1]))
                p2 = (int(bbox1[0] + bbox1[2]), int(bbox1[1] + bbox1[3]))
                cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
            else:
                # Tracking failure
                print('tracking failure')
                #cv2.putText(frame, "Tracking failure detected", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            # save the tracker
            # trackers[i] = tracker

        # Calculate Frames per second (FPS)
        fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer);
        # Display tracker type on frame
        cv2.putText(frame, tracker_type + " Tracker", (100, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);
        # Display FPS on frame
        cv2.putText(frame, "FPS : " + str(int(fps)), (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);
        # Display result
        cv2.imshow("Tracking", frame)
        counter = counter + 1

        # Exit if ESC pressed
        k = cv2.waitKey(1) & 0xff
        if k == 27: break

if __name__ == '__main__':
    run()