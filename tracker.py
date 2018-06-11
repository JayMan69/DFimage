import cv2
import sys
from darkflow.net.build import TFNet
import time
import operator
check_value = 5
no_of_trackers = 2
IOU_THRESHOLD = .5

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

class Trackers:

    def __init__(self,frame,bbox):
        # Initialize bboxes if you want to preset tracking
        self.trackers = {}
        self.ids = 0
        self.new_labels = False
        if bbox != None:
            self.build_trackers(bbox, '', frame)
        else:
            # allow for new targets if new labels
            self.new_labels = True
            Newbboxes = self.get_bound_boxes(frame)
            self.build_trackers(Newbboxes,'Newboxes',frame)


    def assign_tracker(self,bboxes,key,frame):
        tracker = self.create_tracker()
        new_tracker = {}
        # convert p2 into ROI format
        p2 = bboxes[key][2]
        ok = tracker.init(frame, p2)
        new_tracker['status'] = ok
        new_tracker['tracker'] = tracker
        new_tracker['bbox'] = p2
        new_tracker['brox'] = ((bboxes[key][1][0], bboxes[key][1][1]), (bboxes[key][1][2], bboxes[key][1][3]))
        return new_tracker

    def build_trackers(self,boxes_object,box_type,frame):
        if box_type == 'Newboxes':
            for i in range(0, len(boxes_object)):
                tracker = self.create_tracker()
                ok = tracker.init(frame, boxes_object[i][2])
                id1 = self.ids
                self.ids = self.ids + 1
                if ok == True: self.trackers[id1] = ({'status': ok, 'tracker': tracker, 'bbox': boxes_object[i][2]})

        else:
            for i in range(0, len(boxes_object)):
                tracker = self.create_tracker()
                ok = tracker.init(frame, boxes_object[i]['bbox'])
                id1 = boxes_object[i]['id']
                if ok == True: self.trackers[id1] = ({'status': ok, 'tracker': tracker, 'bbox': boxes_object[i]['bbox']})


    def create_tracker(self):
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

    def draw_bound_boxes(self,frame):
        for i in self.trackers.keys():
            if self.trackers[i]['status'] == True:
                bbox2 = self.trackers[i]['bbox']
                # Note not all broxs will be updated
                p1 = (int(bbox2[0]), int(bbox2[1]))
                p2 = (int(bbox2[0] + bbox2[2]), int(bbox2[1] + bbox2[3]))
                cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
                # TODO need to ensure that the identity box is not out of the screen
                sp1 = (int(bbox2[0]-1), int(bbox2[1]-20))
                sp2 = (int(bbox2[0]+30), int(bbox2[1]))
                sp3 = (int(bbox2[0]+ 5), int(bbox2[1]-5))
                cv2.rectangle(frame, sp1, sp2, (255, 0, 0), thickness=cv2.FILLED)
                cv2.putText(frame, str(i), sp3, cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 2)
        return frame


    def get_bound_boxes(self,frame):
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
                # IOU format
                arr2 = (int(result['topleft']['x']), int(result['topleft']['y']),
                 int(result['bottomright']['x']) - int(result['topleft']['x']),
                 int(result['bottomright']['y']) - int(result['topleft']['y']))
                bboxes.append ((i,arr1,arr2))
                i = i + 1
                # format for tracking
                # p1 = (int(bbox[0]), int(bbox[1]))
                # p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))

        return bboxes

    def get_closest_match(self, bboxes, frame):
        # Note this gets the CLOSEST matches!!!!
        tracker_array = {}
        assigned_bboxes = {}
        for i in self.trackers.keys():
            # do this for only valid trackers!
            if self.trackers[i]['status'] == True:
                tracker_array[i] = i
                # initialize bboxes and IOU dictionary
                tracker_array[i] = {}
                bbox = self.trackers[i]['bbox']
                # convert into TL, BR format
                p1 = (int(bbox[0]), int(bbox[1]), int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                for y in range(0, len(bboxes)):
                    p2 = bboxes[y][1]
                    iou = self.get_iou((p1), (p2))
                    tracker_array[i].update({y: iou})

                # get the highest tracker above IOU_Threshold as long as bboxes is not blank
                if len(bboxes) > 0:
                    stats = tracker_array[i]
                    # This get the key of the highest value stored in [1]
                    key = max(stats.items(), key=operator.itemgetter(1))[0]
                    value = max(stats.items(), key=operator.itemgetter(1))[1]
                else:
                    stats = {0:0}
                    key = 0
                    value = 0

                if stats[key] > IOU_THRESHOLD:
                    if key in assigned_bboxes:
                        print('BBox already assigned, invalidating lower iou tracker')
                        if assigned_bboxes[key]['iou'] > value:
                            print('Keeping previous tracker and invalidating tracker', i)
                            # invalidate current tracker
                            self.trackers[i]['status'] = False
                        else:
                            prev_tracker_id = assigned_bboxes[key]['tracker']
                            print('Keeping current tracker and invalidating previous saved tracker!!!', prev_tracker_id)
                            self.trackers[prev_tracker_id]['status'] = False
                            self.trackers[i] = self.assign_tracker(bboxes, key, frame)
                            print('Assigning tracker no,', i, ' to bbox key,', key, 'with stats ', stats[key])
                    else:
                        assigned_bboxes[key] = {'iou':stats[key],'tracker':i}
                        # assigned correct bbox values to tracker
                        self.trackers[i] = self.assign_tracker(bboxes, key, frame)
                        print('Assigning tracker no,', i, ' to bbox key,', key, 'with stats ', stats[key])
                else:
                    # invalidate tracker
                    print ('invalidating tracker no. for max iou',i, ',', stats[key])
                    self.trackers[i]['status'] = False
            else:
                print('skipping invalid status tracker',i)
        # get bboxes not assigned and assign to new tracker
        # check status before assigning
        bbox_key_values = [item[0] for item in bboxes]
        unassigned_bbox_key_values = [i for i in bbox_key_values if i not in assigned_bboxes]
        boxes_object = []
        for i in unassigned_bbox_key_values:
            boxes_object.append(bboxes[i])

        if len(unassigned_bbox_key_values) > 0:
            self.build_trackers(boxes_object, 'Newboxes', frame)

    def get_iou(self,bb1, bb2):
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
        # assert iou >= 0.0
        # assert iou <= 1.0
        return iou


    def get_match(self, bboxes, frame):
        # find matches for existing trackers including clearing out invalid trackers
        # go through all valid trackers and find their equivalent bound box
        # if there is no match for a tracker invalidate it!
        # Note this does not get the closest matches!!!!
        for i in self.trackers.keys():
            # do this for only valid trackers!
            if self.trackers[i]['status'] == True:
                found = False
                bbox = self.trackers[i]['bbox']
                # convert into TL, BR format
                p1 = (int(bbox[0]), int(bbox[1]), int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                for y in range(0, len(bboxes)):
                    p2 = bboxes[y][1]
                    iou = self.get_iou((p1), (p2))

                    if iou > IOU_THRESHOLD:
                        print('iou', iou)
                        found = True
                        # update tracker
                        self.trackers[i] = self.assign_tracker(bboxes, y, frame)
                        break

                if found == False:
                    self.trackers[i]['status'] = False

    def retarget(self,frame):
        Newbboxes = self.get_bound_boxes(frame)
        if self.new_labels == True:
            self.get_closest_match(Newbboxes, frame)
        else:
            self.get_match(Newbboxes, frame)

    def update_trackers(self,frame):
        # Update all trackers
        for i in self.trackers.keys():
            if self.trackers[i]['status'] == True:
            # retrieve trackers for each bound box
                tracker = self.trackers[i]['tracker']
                ok, bbox1 = tracker.update(frame)
                self.trackers[i]['status'] = ok
                if ok == False:
                    print('Invalidating tracker no.',i)
                self.trackers[i]['bbox'] = bbox1


def testHarness():

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
    #video = cv2.VideoCapture("./video/TUD-Stadtmitte.mp4")
    video = cv2.VideoCapture("./video/b2b.mp4")

    if not video.isOpened():
        print("Could not open video")
        sys.exit()

    # Read first frame.
    ok, frame = video.read()
    if not ok:
        print('Cannot read video file')
        sys.exit()

    # initialize trackers for all labels on the initial frame
    mytracker = Trackers(frame,None)
    counter = 0
    while True:
        # Read 2nd frame onwards
        ok, frame = video.read()
        if not ok:
            break

        if counter % check_value == 0 and counter !=0:
            # every nth course correct
            # and reset tracker - set new bbox
            print('reTargetting', counter)
            mytracker.retarget(frame)
        else:
            mytracker.update_trackers(frame)

        frame = mytracker.draw_bound_boxes(frame)
        cv2.putText(frame, "Frame no. : " + str(int(counter)), (100, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2);
        # Display result
        cv2.imshow("Tracking", frame)
        counter = counter + 1

        # Exit if ESC pressed
        k = cv2.waitKey(1) & 0xff
        if k == 27: break

if __name__ == '__main__':
    testHarness()