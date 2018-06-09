import cv2
import sys
from darkflow.net.build import TFNet
import time
import matplotlib.pyplot as plt
check_value = 5
no_of_trackers = 2
IOU_THRESHOLD = .7

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
            i = i + 1
            # format for tracking
            # p1 = (int(bbox[0]), int(bbox[1]))
            # p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))

    return bboxes

def get_match(trackers,bboxes,frame):
    # find matches for existing trackers including clearing out invalid trackers
    # go through all valid trackers and find their equivalent bound box
    # if there is no match for a tracker invalidate it!
    for i in trackers.keys():
        # do this for only valid trackers!
        if trackers[i]['status'] == True:
            found = False
            bbox = trackers[i]['bbox']
            # convert into TL, BR format
            p1 = (int(bbox[0]), int(bbox[1]), int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            for y in range(0,len(bboxes)):
                p2 = bboxes[y][1]
                iou = get_iou((p1), (p2))

                if iou > IOU_THRESHOLD:
                    print('iou', iou)
                    found = True
                    # update tracker
                    tracker = create_tracker()
                    # convert p2 into ROI format
                    p2 = bboxes[y][2]
                    ok = tracker.init(frame, p2)
                    trackers[i]['status'] = ok
                    trackers[i]['tracker'] = tracker
                    trackers[i]['bbox'] = p2
                    trackers[i]['brox'] = ((bboxes[y][1][0],bboxes[y][1][1]),(bboxes[y][1][2],bboxes[y][1][3]))
                    break

            if found == False:
                trackers[i]['status'] = False

    # TODO code for adding new trackers for new bboxes items
    # go through all items in the objects detection bboxes and find associations in trackers
    # skipping for now
    return trackers

def create_tracker():
    tracker_types = ['BOOSTING', 'MIL', 'KCF', 'TLD', 'MEDIANFLOW' ]
    # No 2 = KCF is best
    tracker_type = tracker_types[2]
    if tracker_type == 'BOOSTING':
        return cv2.TrackerBoosting_create()
    if tracker_type == 'MIL':
        return cv2.TrackerMIL_create()
    if tracker_type == 'KCF':
        return cv2.TrackerKCF_create()
    if tracker_type == 'TLD':
        return cv2.TrackerTLD_create()
    if tracker_type == 'MEDIANFLOW':
        return cv2.TrackerMedianFlow_create()


def run():

    # Define an initial bounding box
    bbox = []
    # bbox values provided by selectROI
    #bbox = cv2.selectROI(frame, False)
    # ROI Format. Need to change BR co-ordinates!!!!
    bbox.append({'id':0,'bbox':(81, 93, 91, 234)})
    bbox.append({'id':6,'bbox':(354, 77, 74, 257)})
    # Set up trackers for number of bounding boxes.
    # Instead of MIL, you can also use
    # bbox values provided by TF x,y , manipulated x , manipulated y
    #bbox.append((91, 97, 65, 225))
    #bbox.append((352, 70, 83, 272))


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

    # Initialize trackers with first frame and bounding box
    trackers={}
    for i in range(0,len(bbox)):
        tracker = create_tracker()
        ok = tracker.init(frame, bbox[i]['bbox'])
        id1 = bbox[i]['id']
        if ok == True: trackers[id1] = ({'status':ok,'tracker':tracker,'bbox':bbox[i]['bbox']})

    counter = 0
    while True:
        # Read a new frame
        ok, frame = video.read()
        if not ok:
            break

        # Start timer
        timer = cv2.getTickCount()


        # Update all trackers
        for i in trackers.keys():
            if trackers[i]['status'] == True:
            # retrieve trackers for each bound box
                tracker = trackers[i]['tracker']
                ok, bbox1 = tracker.update(frame)
                trackers[i]['status'] = ok
                trackers[i]['bbox'] = bbox1


        if counter % check_value == 0 :
            # every nth course correct
            # and reset tracker - set new bbox
            print('reTargetting', counter)
            Newbboxes = get_bound_boxes(frame)
            trackers = get_match(trackers, Newbboxes,frame)

        # Update all valid bounded boxes
        for i in trackers.keys():
            if trackers[i]['status'] == True:
                bbox2 = trackers[i]['bbox']
                # Note not all broxs will be updated
                p1 = (int(bbox2[0]), int(bbox2[1]))
                p2 = (int(bbox2[0] + bbox2[2]), int(bbox2[1] + bbox2[3]))
                cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)

                sp1 = (int(bbox2[0]-1), int(bbox2[1]-20))
                sp2 = (int(bbox2[0]+30), int(bbox2[1]))
                sp3 = (int(bbox2[0]+ 5), int(bbox2[1]-5))
                cv2.rectangle(frame, sp1, sp2, (255, 0, 0), thickness=cv2.FILLED)
                cv2.putText(frame, str(i), sp3, cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 2)

        # Calculate Frames per second (FPS)
        fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer);
        # Display tracker type on frame
        cv2.putText(frame, "Frame no. : " + str(int(counter)), (100, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);
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