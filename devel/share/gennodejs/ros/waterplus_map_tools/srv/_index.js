
"use strict";

let SaveWaypoints = require('./SaveWaypoints.js')
let GetWaypointByIndex = require('./GetWaypointByIndex.js')
let GetWaypointByName = require('./GetWaypointByName.js')
let GetChargerByName = require('./GetChargerByName.js')
let AddNewWaypoint = require('./AddNewWaypoint.js')
let GetNumOfWaypoints = require('./GetNumOfWaypoints.js')

module.exports = {
  SaveWaypoints: SaveWaypoints,
  GetWaypointByIndex: GetWaypointByIndex,
  GetWaypointByName: GetWaypointByName,
  GetChargerByName: GetChargerByName,
  AddNewWaypoint: AddNewWaypoint,
  GetNumOfWaypoints: GetNumOfWaypoints,
};
