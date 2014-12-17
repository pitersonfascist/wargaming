'use strict';

/* Controllers */

var wargControllers = angular.module('wargControllers', []);

wargControllers.controller('AccountCtrl', ['$scope', 'Account', 'Logout', 'REGISTEREDUSER', 
  function($scope, Account, Logout, REGISTEREDUSER) {
    $scope.account = Account.query();
    REGISTEREDUSER.setData($scope.account);

    $scope.logout = function(){
      $scope.logout_res = Logout.query();
      $scope.account = new Account();
    }

    $scope.login = function(){
      //window.location.href = "/api/facebook/login";
    }
    
  }]);

wargControllers.controller('UserCtrl', ['$scope', '$routeParams', '$http', 'User', 'REGISTEREDUSER',
  function($scope, $routeParams, $http, User, REGISTEREDUSER) {
    $scope.user= User.query({userId: $routeParams.userId});
    console.log("U: " + $routeParams.userId + " R: " + REGISTEREDUSER.getData().id);
    $scope.isMe = $routeParams.userId == REGISTEREDUSER.getData().id;

    $scope.openSocProfile = function(soc){
      AccountCtrl.openSocProfile(soc);
    }

    $scope.followUser = function(){
      $http.post("/api/user/" + $scope.user.id + "/follow")
      .success(function(data, status, headers, config){
        $scope.user = User.query({userId: $routeParams.userId});
      });
    }

    $scope.unFollowUser = function(){
      $http.post("/api/user/" + $scope.user.id + "/unfollow")
      .success(function(data, status, headers, config){
        $scope.user = User.query({userId: $routeParams.userId});
      });
    }

    $scope.loadFollowers = function(){
      $http.get("/api/user/" + $routeParams.userId + "/followers")
      .success(function(data, status, headers, config){
        $scope.followers = data;
      });
    }

    $scope.loadFollowers();

  }]);

wargControllers.controller('UsersListCtrl', ['$scope', 'Users',
  function($scope, Users) {

    var offset = 0;
    var count = 20;
    var query = "";

    $scope.users = [];

    $scope.loadUsers = function(){
      $scope.users = Users.query({q: query, offset: offset, count: count});
    }

    $scope.loadNext = function(){
      offset += count;
      $scope.loadUsers();
    }

    $scope.loadPrev = function(){
      offset -= count;
      $scope.loadUsers();
    }

    $scope.loadUsers();

  }]);