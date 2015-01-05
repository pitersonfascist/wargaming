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
      var WOT_APP_ID   = "541bb590158341e9e7675ffe10629c02";
      var ACC_FIELDS   = "clan_id,global_rating,last_battle_time,statistics.all.battles,statistics.all.wins,statistics.all.losses";
      var redirectURI  = "http://" + window.location.host + "/api/user/wot"

      window.loginWin = window.open("https://api.worldoftanks.ru/wot/auth/login/?" + "application_id=" + WOT_APP_ID + "&" + "redirect_uri=" + redirectURI
        , "Вход")
      window.loginInterval = setInterval(window.checkIsLogin, 500);
    }

    window.checkIsLogin = function(){
        try{
          if(window.loginWin.location.host == window.location.host){
            clearInterval(window.loginInterval);
            window.loginWin.close();
            window.loginWin = null;
            $scope.account = Account.query();
            REGISTEREDUSER.setData($scope.account);
          }
        }catch(err){

        }
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

    $scope.offset = 0;
    var count = 20;
    var query = "";

    $scope.users = [];

    $scope.loadUsers = function(){
      $scope.users = Users.query({q: query, offset: $scope.offset, count: count});
    }
    
    $scope.loadOnline = function(){
      $scope.users = Users.online();
    }

    $scope.loadNext = function(){
      $scope.offset += count;
      $scope.loadUsers();
    }

    $scope.loadPrev = function(){
      $scope.offset -= count;
      $scope.loadUsers();
    }

    $scope.searchUser = function(q){
       query = q;
       $scope.loadUsers();
    }
    
    $scope.onlineChecked = function(){
        if($scope.isOnline)
            $scope.loadOnline();
        else
            $scope.loadUsers();
    }

    $scope.loadUsers();

  }]);

wargControllers.controller('StatsCtrl', ['$scope', 'Stats',
  function($scope, Stats) {
    $scope.stats = Stats.query();

  }]);